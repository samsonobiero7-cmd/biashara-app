const THEME_STORAGE_KEY = "biashara-theme-mode";
const THEME_MODES = ["light", "dark"];

export default function({ data, setStateValue }) {
  const bridge = window.__biasharaThemeBridge ||
    (window.__biasharaThemeBridge = {
      initialized: false,
      lastPythonMode: null,
      currentMode: "light",
      setStateValue: null,
      listenerAttached: false,
    });
  bridge.setStateValue = setStateValue;

  const mode = data.theme_mode === "dark" ? "dark" : "light";
  const storedMode = localStorage.getItem(THEME_STORAGE_KEY);
  if (!bridge.initialized) {
    bridge.initialized = true;
    bridge.lastPythonMode = mode;
    if (THEME_MODES.includes(storedMode)) {
      if (storedMode !== mode) {
        setStateValue("theme_mode", storedMode);
      }
    } else {
      localStorage.setItem(THEME_STORAGE_KEY, mode);
    }
  } else if (bridge.lastPythonMode !== mode) {
    bridge.lastPythonMode = mode;
    if (storedMode !== mode) {
      localStorage.setItem(THEME_STORAGE_KEY, mode);
    }
  } else if (THEME_MODES.includes(storedMode) && storedMode !== mode) {
    setStateValue("theme_mode", storedMode);
  }
  bridge.currentMode = mode;

  if (!bridge.listenerAttached) {
    window.addEventListener("storage", (event) => {
      if (
        event.key === THEME_STORAGE_KEY &&
        THEME_MODES.includes(event.newValue) &&
        event.newValue !== bridge.currentMode
      ) {
        bridge.setStateValue("theme_mode", event.newValue);
      }
    });
    bridge.listenerAttached = true;
  }
}
