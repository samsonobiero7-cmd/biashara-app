const DATABASE_NAME = "biashara-offline";
const DATABASE_VERSION = 2;
const THEME_STORAGE_KEY = "biashara-offline-theme-mode";
const catalogStoreName = "catalogs";
const saleStoreName = "sales";
const productStoreName = "products";

let activeCatalog = null;
let cart = [];
let productsBySuggestion = new Map();

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(catalogStoreName)) {
        database.createObjectStore(catalogStoreName, { keyPath: "key" });
      }
      if (!database.objectStoreNames.contains(saleStoreName)) {
        database.createObjectStore(saleStoreName, { keyPath: "client_sale_id" });
      }
      if (!database.objectStoreNames.contains(productStoreName)) {
        database.createObjectStore(productStoreName, { keyPath: "client_product_id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function requestResult(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function getAll(storeName) {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(storeName, "readonly");
    return await requestResult(transaction.objectStore(storeName).getAll());
  } finally {
    database.close();
  }
}

async function getCatalog(key) {
  const database = await openDatabase();
  try {
    const transaction = database.transaction(catalogStoreName, "readonly");
    return await requestResult(transaction.objectStore(catalogStoreName).get(key));
  } finally {
    database.close();
  }
}

async function saveSaleAndCatalog(sale, catalog) {
  const database = await openDatabase();
  try {
    await new Promise((resolve, reject) => {
      const transaction = database.transaction(
        [catalogStoreName, saleStoreName],
        "readwrite",
      );
      transaction.objectStore(saleStoreName).put(sale);
      transaction.objectStore(catalogStoreName).put(catalog);
      transaction.oncomplete = resolve;
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally {
    database.close();
  }
}

async function savePendingReference(clientSaleId, reference) {
  const database = await openDatabase();
  try {
    await new Promise((resolve, reject) => {
      const transaction = database.transaction(saleStoreName, "readwrite");
      const store = transaction.objectStore(saleStoreName);
      const request = store.get(clientSaleId);
      request.onsuccess = () => {
        if (!request.result) {
          transaction.abort();
          reject(new Error("Pending sale was not found."));
          return;
        }
        request.result.payment_reference = reference.trim().toUpperCase() || null;
        store.put(request.result);
      };
      request.onerror = () => reject(request.error);
      transaction.oncomplete = resolve;
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally {
    database.close();
  }
  await renderPendingCount();
  document.getElementById("sale-message").textContent =
    "Reference updated. Open Biashara Manager online to retry syncing.";
}

function setConnectionStatus() {
  const status = document.getElementById("connection-status");
  status.textContent = navigator.onLine
    ? "Internet available"
    : "Offline — sales save on this device";
  status.classList.toggle("offline", !navigator.onLine);
}

function applyTheme(mode) {
  const isDark = mode === "dark";
  document.documentElement.dataset.theme = isDark ? "dark" : "light";

  const toggle = document.getElementById("theme-toggle");
  toggle.textContent = isDark ? "Light mode" : "Dark mode";
  toggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
  toggle.setAttribute("aria-pressed", String(isDark));

  document
    .querySelector('meta[name="theme-color"]')
    .setAttribute("content", isDark ? "#111813" : "#ffffff");
}

function initializeTheme() {
  const storedMode = localStorage.getItem(THEME_STORAGE_KEY);
  const mode = storedMode === "dark" ? "dark" : "light";
  if (storedMode !== mode) {
    localStorage.setItem(THEME_STORAGE_KEY, mode);
  }
  applyTheme(mode);

  document.getElementById("theme-toggle").addEventListener("click", () => {
    const nextMode =
      document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_STORAGE_KEY, nextMode);
    applyTheme(nextMode);
  });

  window.addEventListener("storage", (event) => {
    if (
      event.key === THEME_STORAGE_KEY &&
      (event.newValue === "light" || event.newValue === "dark")
    ) {
      applyTheme(event.newValue);
    }
  });
}

function formatMoney(value) {
  return `KSh ${Number(value || 0).toLocaleString("en-KE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function productKey(product) {
  return product.client_product_id
    ? `client:${product.client_product_id}`
    : `product:${Number(product.product_id)}`;
}

function normalizeProductSuggestion(value) {
  return value.trim().toLocaleLowerCase();
}

function cartItemProductKey(item) {
  return item.client_product_id
    ? `client:${item.client_product_id}`
    : `product:${Number(item.product_id)}`;
}

function selectedProduct() {
  const input = document.getElementById("product-input");
  return productsBySuggestion.get(normalizeProductSuggestion(input.value));
}

function renderProducts() {
  const productInput = document.getElementById("product-input");
  const suggestions = document.getElementById("product-suggestions");
  const priceInput = document.getElementById("unit-price");
  const countsByName = new Map();
  productsBySuggestion = new Map();
  suggestions.replaceChildren();
  productInput.value = "";
  priceInput.value = "";

  activeCatalog.products.forEach((product) => {
    const nameKey = normalizeProductSuggestion(product.product_name);
    countsByName.set(nameKey, (countsByName.get(nameKey) || 0) + 1);
  });

  activeCatalog.products.forEach((product) => {
    const nameKey = normalizeProductSuggestion(product.product_name);
    let value = product.product_name;
    if (countsByName.get(nameKey) > 1) {
      value += ` — ${product.stock_quantity} in stock, ${formatMoney(product.selling_price)}`;
    }
    const baseValue = value;
    let suffix = 2;
    while (productsBySuggestion.has(normalizeProductSuggestion(value))) {
      value = `${baseValue} (${suffix})`;
      suffix += 1;
    }

    const option = document.createElement("option");
    option.value = value;
    option.label = `${product.product_name} — ${product.stock_quantity} packs/items in stock`;
    suggestions.append(option);
    productsBySuggestion.set(normalizeProductSuggestion(value), product);
  });

  document.getElementById("product-hint").textContent =
    "Type to search products saved on this device. If a product is not listed, add it online and refresh the Sales page.";
}

function updateProductSelection() {
  const product = selectedProduct();
  const priceInput = document.getElementById("unit-price");
  const hint = document.getElementById("product-hint");
  if (product) {
    priceInput.value = Number(product.selling_price || 0);
    hint.textContent = `${product.product_name}: ${product.stock_quantity} packs/items saved on this device.`;
    return;
  }

  priceInput.value = "";
  hint.textContent = document.getElementById("product-input").value.trim()
    ? "Choose a product from the saved suggestions. New products must be added online."
    : "Type to search products saved on this device.";
}

function renderCart() {
  const list = document.getElementById("cart-items");
  list.replaceChildren();
  let total = 0;

  cart.forEach((item, index) => {
    const product = activeCatalog.products.find(
      (candidate) => productKey(candidate) === cartItemProductKey(item),
    );
    if (!product) {
      return;
    }
    total += item.quantity * item.unit_price;
    const row = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = `${product.product_name} × ${item.quantity} — ${formatMoney(
      item.quantity * item.unit_price,
    )}`;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.setAttribute("aria-label", `Remove ${product.product_name}`);
    remove.addEventListener("click", () => {
      cart.splice(index, 1);
      renderCart();
    });
    row.append(label, remove);
    list.append(row);
  });

  document.getElementById("sale-total").textContent = `Total: ${formatMoney(total)}`;
  document.getElementById("save-sale").disabled = cart.length === 0;
}

async function renderPendingCount() {
  const [sales, products] = await Promise.all([
    getAll(saleStoreName),
    getAll(productStoreName),
  ]);
  const pending = sales.filter(
    (sale) =>
      sale.owner_email === activeCatalog.owner_email &&
      Number(sale.business_id) === Number(activeCatalog.business_id),
  );
  const pendingProducts = products.filter(
    (product) =>
      product.owner_email === activeCatalog.owner_email &&
      Number(product.business_id) === Number(activeCatalog.business_id),
  );
  const pendingCount = document.getElementById("pending-count");
  pendingCount.textContent =
    pending.length === 0
      ? "No unsynced sales."
      : `${pending.length} sale${pending.length === 1 ? "" : "s"} waiting to sync.`;
  if (pendingProducts.length > 0) {
    pendingCount.textContent +=
      ` ${pendingProducts.length} previously queued product` +
      `${pendingProducts.length === 1 ? "" : "s"} also waiting to sync.`;
  }
  const list = document.getElementById("pending-sales");
  list.replaceChildren();
  pending.forEach((sale) => {
    const row = document.createElement("li");
    row.className = "pending-row";
    const total = sale.items.reduce(
      (sum, item) => sum + Number(item.quantity) * Number(item.unit_price),
      0,
    );
    const summary = document.createElement("div");
    summary.textContent = `${new Date(sale.created_at).toLocaleString()} — ${formatMoney(total)}`;
    const reference = document.createElement("input");
    reference.type = "text";
    reference.value = sale.payment_reference || "";
    reference.placeholder = "Payment reference";
    reference.setAttribute("aria-label", "Payment reference for pending sale");
    const save = document.createElement("button");
    save.type = "button";
    save.className = "button";
    save.textContent = "Update reference";
    save.addEventListener("click", () => {
      savePendingReference(sale.client_sale_id, reference.value).catch((error) => {
        document.getElementById("sale-message").textContent =
          `Reference was not saved: ${error.message}`;
      });
    });
    row.append(summary, reference, save);
    list.append(row);
  });

  const productList = document.getElementById("pending-products");
  productList.replaceChildren();
  pendingProducts.forEach((product) => {
    const row = document.createElement("li");
    row.textContent = `${product.product_name} — waiting to sync`;
    productList.append(row);
  });
}

async function selectCatalog(key) {
  activeCatalog = await getCatalog(key);
  if (!activeCatalog) {
    throw new Error("The saved business information could not be opened.");
  }

  localStorage.setItem("biashara-offline-catalog", key);
  renderProducts();
  renderCart();
  await renderPendingCount();
}

async function loadCatalogs() {
  const catalogs = await getAll(catalogStoreName);
  const businessSelect = document.getElementById("business-select");
  businessSelect.replaceChildren();

  if (catalogs.length === 0) {
    document.getElementById("setup-message").hidden = false;
    return;
  }

  document.getElementById("setup-message").hidden = true;
  document.getElementById("checkout").hidden = false;
  catalogs.sort((a, b) => a.business_name.localeCompare(b.business_name));
  catalogs.forEach((catalog) => {
    const option = document.createElement("option");
    option.value = catalog.key;
    option.textContent = catalog.business_name;
    businessSelect.append(option);
  });

  const savedKey = localStorage.getItem("biashara-offline-catalog");
  const selected = catalogs.find((catalog) => catalog.key === savedKey) || catalogs[0];
  businessSelect.value = selected.key;
  await selectCatalog(selected.key);
}

async function addItemToCart() {
  const product = selectedProduct();
  const quantity = Number(document.getElementById("quantity").value);
  const unitPrice = Number(document.getElementById("unit-price").value);
  const message = document.getElementById("sale-message");
  message.textContent = "";

  if (!product || !Number.isFinite(quantity) || quantity <= 0) {
    message.textContent =
      "Choose a saved product suggestion and enter a quantity above zero.";
    return;
  }
  if (!Number.isFinite(unitPrice) || unitPrice < 0) {
    message.textContent = "Enter a valid selling price.";
    return;
  }

  const selectedKey = productKey(product);
  const alreadyInCart = cart
    .filter((item) => cartItemProductKey(item) === selectedKey)
    .reduce((sum, item) => sum + item.quantity, 0);
  if (quantity + alreadyInCart > Number(product.stock_quantity)) {
    message.textContent = `Only ${product.stock_quantity} packs/items are in this device's saved stock.`;
    return;
  }

  cart.push({
    ...(product.client_product_id
      ? { client_product_id: product.client_product_id }
      : { product_id: Number(product.product_id) }),
    quantity,
    unit_price: unitPrice,
  });
  document.getElementById("product-input").value = "";
  document.getElementById("quantity").value = "1";
  document.getElementById("unit-price").value = "";
  document.getElementById("product-hint").textContent =
    `${product.product_name} added. Search for another product or save the sale.`;
  renderCart();
  document.getElementById("product-input").focus();
}

async function saveSaleOffline() {
  const message = document.getElementById("sale-message");
  message.textContent = "";
  if (cart.length === 0) {
    message.textContent = "Add at least one product to the sale.";
    return;
  }

  const paymentMethod = document.getElementById("payment-method").value;
  const paymentReference =
    document.getElementById("payment-reference").value.trim().toUpperCase();
  if (paymentMethod !== "Cash" && !paymentReference) {
    message.textContent = "Add the payment reference for this payment method.";
    return;
  }

  const sale = {
    client_sale_id: crypto.randomUUID(),
    owner_email: activeCatalog.owner_email,
    business_id: Number(activeCatalog.business_id),
    items: cart.map((item) => ({ ...item })),
    payment_method: paymentMethod,
    payment_reference: paymentReference || null,
    created_at: new Date().toISOString(),
  };

  const updatedCatalog = {
    ...activeCatalog,
    products: activeCatalog.products.map((product) => {
      const sold = cart
        .filter((item) => cartItemProductKey(item) === productKey(product))
        .reduce((sum, item) => sum + item.quantity, 0);
      return sold
        ? { ...product, stock_quantity: Number(product.stock_quantity) - sold }
        : product;
    }),
  };

  await saveSaleAndCatalog(sale, updatedCatalog);
  activeCatalog = updatedCatalog;
  cart = [];
  renderProducts();
  renderCart();
  await renderPendingCount();
  document.getElementById("payment-reference").value = "";
  message.textContent = "Sale saved on this device. It will sync when you're online.";
}

async function start() {
  initializeTheme();
  setConnectionStatus();
  window.addEventListener("online", setConnectionStatus);
  window.addEventListener("offline", setConnectionStatus);

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./sw.js").catch((error) => {
      document.getElementById("sale-message").textContent =
        `Offline page could not be prepared: ${error.message}`;
    });
  }

  document.getElementById("business-select").addEventListener("change", (event) => {
    selectCatalog(event.target.value).catch((error) => {
      document.getElementById("sale-message").textContent = error.message;
    });
  });
  document.getElementById("product-input").addEventListener("input", updateProductSelection);
  document.getElementById("add-item").addEventListener("click", () => {
    addItemToCart().catch((error) => {
      document.getElementById("sale-message").textContent = error.message;
    });
  });
  document.getElementById("save-sale").addEventListener("click", () => {
    saveSaleOffline().catch((error) => {
      document.getElementById("sale-message").textContent =
        `Sale was not saved: ${error.message}`;
    });
  });
  try {
    await loadCatalogs();
  } catch (error) {
    document.getElementById("setup-message").hidden = false;
    document.getElementById("sale-message").textContent = error.message;
  }
}

start();
