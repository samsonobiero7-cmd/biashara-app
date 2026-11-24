const DATABASE_NAME = "biashara-offline";
const DATABASE_VERSION = 2;
const CATALOG_STORE = "catalogs";
const SALES_STORE = "sales";
const PRODUCTS_STORE = "products";

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(CATALOG_STORE)) {
        database.createObjectStore(CATALOG_STORE, { keyPath: "key" });
      }
      if (!database.objectStoreNames.contains(SALES_STORE)) {
        database.createObjectStore(SALES_STORE, { keyPath: "client_sale_id" });
      }
      if (!database.objectStoreNames.contains(PRODUCTS_STORE)) {
        database.createObjectStore(PRODUCTS_STORE, { keyPath: "client_product_id" });
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

function writeTransaction(database, work) {
  return new Promise((resolve, reject) => {
    const transaction = database.transaction(
      [CATALOG_STORE, SALES_STORE, PRODUCTS_STORE],
      "readwrite",
    );
    work(transaction);
    transaction.oncomplete = resolve;
    transaction.onerror = () => reject(transaction.error);
    transaction.onabort = () => reject(transaction.error);
  });
}

export default function(component) {
  const { data, setStateValue } = component;
  if (!data || !data.owner_email || !data.business_id) {
    return;
  }

  async function prepareCatalogAndSyncQueue() {
    const database = await openDatabase();
    try {
      const ackIds = new Set(data.ack_ids || []);
      const ackProductIds = new Set(data.ack_product_ids || []);
      const sales = database.transaction(SALES_STORE, "readonly");
      const queuedSales = await requestResult(sales.objectStore(SALES_STORE).getAll());
      const relevantSales = queuedSales.filter(
        (sale) =>
          sale.owner_email === data.owner_email &&
          Number(sale.business_id) === Number(data.business_id),
      );
      const products = database.transaction(PRODUCTS_STORE, "readonly");
      const queuedProducts = await requestResult(
        products.objectStore(PRODUCTS_STORE).getAll(),
      );
      const relevantProducts = queuedProducts.filter(
        (product) =>
          product.owner_email === data.owner_email &&
          Number(product.business_id) === Number(data.business_id),
      );

      await writeTransaction(database, (transaction) => {
        const saleStore = transaction.objectStore(SALES_STORE);
        const productStore = transaction.objectStore(PRODUCTS_STORE);
        ackIds.forEach((id) => saleStore.delete(id));
        ackProductIds.forEach((id) => productStore.delete(id));
      });

      const remainingSales = relevantSales.filter(
        (sale) => !ackIds.has(sale.client_sale_id),
      );
      const remainingProducts = relevantProducts.filter(
        (product) => !ackProductIds.has(product.client_product_id),
      );
      const onlineProducts = Array.isArray(data.products) ? data.products : [];
      const offlineProductIds = new Map(
        onlineProducts
          .filter((product) => product.offline_product_id)
          .map((product) => [
            String(product.offline_product_id),
            Number(product.product_id),
          ]),
      );
      const normalizedSales = remainingSales.map((sale) => ({
        ...sale,
        items: sale.items.map((item) => {
          const productId = offlineProductIds.get(
            String(item.client_product_id || ""),
          );
          if (!productId) {
            return item;
          }
          const { client_product_id, ...rest } = item;
          return { ...rest, product_id: productId };
        }),
      }));

      await writeTransaction(database, (transaction) => {
        const saleStore = transaction.objectStore(SALES_STORE);
        normalizedSales.forEach((sale) => saleStore.put(sale));
      });

      const pendingByProduct = new Map();
      normalizedSales.forEach((sale) => {
        sale.items.forEach((item) => {
          const key = item.client_product_id
            ? `client:${item.client_product_id}`
            : `product:${Number(item.product_id)}`;
          pendingByProduct.set(key, (pendingByProduct.get(key) || 0) + Number(item.quantity));
        });
      });

      const catalog = {
        key: `${data.owner_email}::${data.business_id}`,
        owner_email: data.owner_email,
        business_id: Number(data.business_id),
        business_name: data.business_name,
        updated_at: new Date().toISOString(),
        products: [
          ...onlineProducts.map((product) => ({
            ...product,
            stock_quantity:
              Number(product.stock_quantity) -
              (pendingByProduct.get(`product:${Number(product.product_id)}`) || 0),
          })),
          ...remainingProducts
            .filter(
              (product) => !offlineProductIds.has(product.client_product_id),
            )
            .map((product) => ({
              ...product,
              product_id: null,
              stock_quantity:
                Number(product.stock_quantity) -
                (pendingByProduct.get(
                  `client:${product.client_product_id}`,
                ) || 0),
            })),
        ],
      };

      await writeTransaction(database, (transaction) => {
        transaction.objectStore(CATALOG_STORE).put(catalog);
      });
      setStateValue("catalog_ready", true);

      const signature = JSON.stringify(
        normalizedSales.sort((a, b) =>
          a.client_sale_id.localeCompare(b.client_sale_id),
        ),
      );
      if (data.pending_signature !== signature) {
        setStateValue("pending_signature", signature);
        setStateValue("pending_sales", normalizedSales);
      }

      const productSignature = JSON.stringify(
        remainingProducts.sort((a, b) =>
          a.client_product_id.localeCompare(b.client_product_id),
        ),
      );
      if (data.pending_products_signature !== productSignature) {
        setStateValue("pending_products_signature", productSignature);
        setStateValue("pending_products", remainingProducts);
      }
      setStateValue("bridge_error", null);
    } finally {
      database.close();
    }
  }

  prepareCatalogAndSyncQueue().catch((error) => {
    setStateValue("bridge_error", error.message || "Offline storage is unavailable.");
  });
}
