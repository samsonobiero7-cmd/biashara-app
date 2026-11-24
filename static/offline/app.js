const DATABASE_NAME = "biashara-offline";
const DATABASE_VERSION = 1;
const catalogStoreName = "catalogs";
const saleStoreName = "sales";

let activeCatalog = null;
let cart = [];

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

function formatMoney(value) {
  return `KSh ${Number(value || 0).toLocaleString("en-KE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function selectedProduct() {
  const productId = Number(document.getElementById("product-select").value);
  return activeCatalog.products.find((product) => Number(product.product_id) === productId);
}

function renderProducts() {
  const productSelect = document.getElementById("product-select");
  const priceInput = document.getElementById("unit-price");
  productSelect.replaceChildren();

  activeCatalog.products.forEach((product) => {
    const option = document.createElement("option");
    option.value = product.product_id;
    option.textContent = `${product.product_name} — ${product.stock_quantity} in stock`;
    productSelect.append(option);
  });

  const product = selectedProduct();
  priceInput.value = product ? Number(product.selling_price || 0) : "";
}

function renderCart() {
  const list = document.getElementById("cart-items");
  list.replaceChildren();
  let total = 0;

  cart.forEach((item, index) => {
    const product = activeCatalog.products.find(
      (candidate) => Number(candidate.product_id) === Number(item.product_id),
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
  const sales = await getAll(saleStoreName);
  const pending = sales.filter(
    (sale) =>
      sale.owner_email === activeCatalog.owner_email &&
      Number(sale.business_id) === Number(activeCatalog.business_id),
  );
  document.getElementById("pending-count").textContent =
    pending.length === 1
      ? "1 sale is waiting to sync."
      : `${pending.length} sales are waiting to sync.`;
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
}

async function selectCatalog(key) {
  activeCatalog = await getCatalog(key);
  if (!activeCatalog) {
    throw new Error("The saved business information could not be opened.");
  }

  localStorage.setItem("biashara-offline-catalog", key);
  document.getElementById("business-owner").textContent = activeCatalog.owner_email;
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

  document.getElementById("checkout").hidden = false;
  catalogs.sort((a, b) => a.business_name.localeCompare(b.business_name));
  catalogs.forEach((catalog) => {
    const option = document.createElement("option");
    option.value = catalog.key;
    option.textContent = `${catalog.business_name} (${catalog.owner_email})`;
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
    message.textContent = "Choose a product and enter a quantity above zero.";
    return;
  }
  if (!Number.isFinite(unitPrice) || unitPrice < 0) {
    message.textContent = "Enter a valid selling price.";
    return;
  }

  const alreadyInCart = cart
    .filter((item) => Number(item.product_id) === Number(product.product_id))
    .reduce((sum, item) => sum + item.quantity, 0);
  if (quantity + alreadyInCart > Number(product.stock_quantity)) {
    message.textContent = `Only ${product.stock_quantity} units are in this device's saved stock.`;
    return;
  }

  cart.push({
    product_id: Number(product.product_id),
    quantity,
    unit_price: unitPrice,
  });
  document.getElementById("quantity").value = "1";
  renderCart();
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
        .filter((item) => Number(item.product_id) === Number(product.product_id))
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
  document.getElementById("product-select").addEventListener("change", () => {
    const product = selectedProduct();
    document.getElementById("unit-price").value = product
      ? Number(product.selling_price || 0)
      : "";
  });
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
