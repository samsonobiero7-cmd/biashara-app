const DATABASE_NAME = "biashara-offline";
const DATABASE_VERSION = 1;
const CATALOG_STORE = "catalogs";
const SALES_STORE = "sales";
const sentSignatures = new Map();

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
    const transaction = database.transaction([CATALOG_STORE, SALES_STORE], "readwrite");
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

  const componentKey = `${data.owner_email}::${data.business_id}`;

  async function prepareCatalogAndSyncQueue() {
    const database = await openDatabase();
    try {
      const ackIds = new Set(data.ack_ids || []);
      const sales = database.transaction(SALES_STORE, "readonly");
      const queuedSales = await requestResult(sales.objectStore(SALES_STORE).getAll());
      const relevantSales = queuedSales.filter(
        (sale) =>
          sale.owner_email === data.owner_email &&
          Number(sale.business_id) === Number(data.business_id),
      );

      await writeTransaction(database, (transaction) => {
        const saleStore = transaction.objectStore(SALES_STORE);
        ackIds.forEach((id) => saleStore.delete(id));
      });

      const remainingSales = relevantSales.filter(
        (sale) => !ackIds.has(sale.client_sale_id),
      );
      const pendingByProduct = new Map();
      remainingSales.forEach((sale) => {
        sale.items.forEach((item) => {
          const productId = Number(item.product_id);
          pendingByProduct.set(
            productId,
            (pendingByProduct.get(productId) || 0) + Number(item.quantity),
          );
        });
      });

      const catalog = {
        key: `${data.owner_email}::${data.business_id}`,
        owner_email: data.owner_email,
        business_id: Number(data.business_id),
        business_name: data.business_name,
        updated_at: new Date().toISOString(),
        products: data.products.map((product) => ({
          ...product,
          stock_quantity:
            Number(product.stock_quantity) -
            (pendingByProduct.get(Number(product.product_id)) || 0),
        })),
      };

      await writeTransaction(database, (transaction) => {
        transaction.objectStore(CATALOG_STORE).put(catalog);
      });
      setStateValue("catalog_ready", true);

      const signature = JSON.stringify(
        remainingSales.sort((a, b) =>
          a.client_sale_id.localeCompare(b.client_sale_id),
        ),
      );
      if (sentSignatures.get(componentKey) !== signature) {
        sentSignatures.set(componentKey, signature);
        setStateValue("pending_sales", remainingSales);
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
