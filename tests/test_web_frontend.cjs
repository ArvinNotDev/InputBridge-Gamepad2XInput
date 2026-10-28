const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const appSource = fs.readFileSync(
  path.join(__dirname, "../ui/web/static/app.js"),
  "utf8",
);

function createElement(id, attributes = {}) {
  const classes = new Set();
  const listeners = new Map();
  return {
    id,
    attributes,
    listeners,
    style: {},
    value: "",
    textContent: "",
    disabled: false,
    title: "",
    classList: {
      add(name) { classes.add(name); },
      remove(name) { classes.delete(name); },
      contains(name) { return classes.has(name); },
      toggle(name, force) {
        const enabled = force === undefined ? !classes.has(name) : !!force;
        if (enabled) classes.add(name);
        else classes.delete(name);
        return enabled;
      },
    },
    addEventListener(name, handler) {
      if (!listeners.has(name)) listeners.set(name, []);
      listeners.get(name).push(handler);
    },
    dispatch(name, values = {}) {
      const event = {
        pointerId: 1,
        clientX: 100,
        clientY: 100,
        preventDefault() {},
        ...values,
      };
      if (name === "click" && this.disabled) return event;
      if (name === "click" && typeof this.onclick === "function") this.onclick(event);
      for (const handler of listeners.get(name) || []) handler(event);
      return event;
    },
    getAttribute(name) { return attributes[name] ?? null; },
    setAttribute(name, value) { attributes[name] = String(value); },
    setPointerCapture() {},
    getBoundingClientRect() { return { left: 0, top: 0, width: 200, height: 200 }; },
    querySelector(selector) {
      if (selector === ".knob") return this.knob || createElement(`${id}-knob`);
      if (selector === "span") return createElement(`${id}-span`);
      return null;
    },
  };
}

function createHarness(settings = {}) {
  const calls = [];
  const elements = new Map();
  const gamepadButton = createElement("button-A", { "data-button": "A" });
  const quickKeys = ["LEFT", "UP", "DOWN", "RIGHT"].map((key) =>
    createElement(`key-${key}`, { "data-key": key, "data-permission": "keyboard" }),
  );
  const leftStick = createElement("leftStick");
  const rightStick = createElement("rightStick");
  leftStick.knob = createElement("left-knob");
  rightStick.knob = createElement("right-knob");
  const touchpad = createElement("touchpad");
  elements.set("leftStick", leftStick);
  elements.set("rightStick", rightStick);
  elements.set("touchpad", touchpad);
  const mouseTab = createElement("mouse-tab", { "data-tab": "mouse" });
  const views = ["gamepad", "mouse", "remote", "session"].map((name) =>
    createElement(`view-${name}`),
  );
  const documentListeners = new Map();
  const body = createElement("body");
  const documentElement = createElement("documentElement");
  const sessionValues = new Map([
    ["ib.web.token", "test-session-token"],
    ["ib.web.name", "Test browser"],
  ]);
  let now = 1000;
  let failNextState = false;
  const frames = [];

  const document = {
    readyState: "complete",
    hidden: false,
    body,
    documentElement,
    fullscreenElement: null,
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, createElement(id));
      return elements.get(id);
    },
    querySelectorAll(selector) {
      if (selector === ".tab") return [mouseTab];
      if (selector === ".view") return views;
      if (selector === ".pad-key[data-button]") return [gamepadButton];
      if (selector === "[data-key]") return quickKeys;
      if (selector === "[data-permission]") return quickKeys;
      if (selector === ".knob") return [leftStick.knob, rightStick.knob];
      if (selector === ".pad-key.pressed,.btn.pressed") {
        return [gamepadButton].filter((element) => element.classList.contains("pressed"));
      }
      return [];
    },
    addEventListener(name, handler) {
      if (!documentListeners.has(name)) documentListeners.set(name, []);
      documentListeners.get(name).push(handler);
    },
    dispatch(name) {
      for (const handler of documentListeners.get(name) || []) handler({ type: name });
    },
  };
  const window = {
    location: { hash: "", pathname: "/", search: "" },
    addEventListener() {},
    removeEventListener() {},
    confirm() { return true; },
  };
  const fetch = (url, options = {}) => {
    calls.push({ url, options });
    if (url === "/api/state" && failNextState) {
      failNextState = false;
      return Promise.reject(new Error("connection lost"));
    }
    const body = url === "/api/action"
      ? { ok: true, result: { capabilities: settings.capabilities || {
        pc_status: true, keyboard: true, media: true, clipboard: true,
        app_launch: true, presentation: true, power: true,
      } } }
      : { ok: true };
    return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
  };
  const sandbox = {
    document,
    window,
    fetch,
    sessionStorage: {
      getItem(key) { return sessionValues.get(key) || null; },
      setItem(key, value) { sessionValues.set(key, value); },
      removeItem(key) { sessionValues.delete(key); },
    },
    URLSearchParams,
    performance: { now() { now += 5; return now; } },
    requestAnimationFrame(callback) { frames.push(callback); },
    setTimeout,
    clearTimeout,
    history: { replaceState() {} },
  };

  vm.runInNewContext(appSource, sandbox, { filename: "ui/web/static/app.js" });
  return {
    calls,
    document,
    elements,
    gamepadButton,
    leftStick,
    mouseTab,
    quickKeys,
    sessionValues,
    touchpad,
    tickFrame() {
      const callback = frames.shift();
      if (callback) callback();
    },
    setFailNextState() { failNextState = true; },
  };
}

async function settle() {
  for (let i = 0; i < 8; i += 1) await new Promise((resolve) => setImmediate(resolve));
}

function stateRequests(harness) {
  return harness.calls
    .filter(({ url }) => url === "/api/state")
    .map(({ options }) => JSON.parse(options.body));
}

test("web keyboard navigation buttons send authenticated arrow-key actions", async () => {
  const harness = createHarness();
  await settle();

  for (const key of ["LEFT", "UP", "DOWN", "RIGHT"]) {
    const button = harness.quickKeys.find((item) => item.getAttribute("data-key") === key);
    button.dispatch("click", { detail: 1 });
    await settle();
  }

  const requests = harness.calls
    .filter(({ url }) => url === "/api/action")
    .map(({ options }) => ({ options, body: JSON.parse(options.body) }))
    .filter(({ body }) => body.action === "keyboard_key");
  assert.deepEqual(requests.map(({ body }) => body.payload.key), ["LEFT", "UP", "DOWN", "RIGHT"]);
  assert.ok(requests.every(({ options }) =>
    options.headers.Authorization === "Bearer test-session-token"));
});

test("web keyboard navigation buttons stay disabled without PC keyboard permission", async () => {
  const harness = createHarness({
    capabilities: {
      pc_status: true, keyboard: false, media: false, clipboard: false,
      app_launch: false, presentation: false, power: false,
    },
  });
  await settle();

  const leftArrow = harness.quickKeys.find((button) => button.getAttribute("data-key") === "LEFT");
  assert.equal(leftArrow.disabled, true);
  leftArrow.dispatch("click", { detail: 1 });
  await settle();
  assert.equal(harness.calls.some(({ url, options }) =>
    url === "/api/action" && JSON.parse(options.body).action === "keyboard_key"), false);
});

test("a gamepad button stays held until every touch pointer releases it", async () => {
  const harness = createHarness();
  await settle();
  harness.gamepadButton.dispatch("pointerdown", { pointerId: 10 });
  harness.gamepadButton.dispatch("pointerdown", { pointerId: 11 });
  harness.gamepadButton.dispatch("pointerup", { pointerId: 10 });
  await settle();
  assert.equal(stateRequests(harness).at(-1).buttons.A, 1);

  harness.gamepadButton.dispatch("pointerup", { pointerId: 11 });
  await settle();
  assert.equal(stateRequests(harness).at(-1).buttons.A, 0);
});

test("gamepad buttons respond to keyboard activation and release on keyup", async () => {
  const harness = createHarness();
  await settle();

  harness.gamepadButton.dispatch("keydown", { key: "Enter" });
  await settle();
  assert.equal(stateRequests(harness).at(-1).buttons.A, 1);

  harness.gamepadButton.dispatch("keyup", { key: "Enter" });
  await settle();
  assert.equal(stateRequests(harness).at(-1).buttons.A, 0);
});

test("cancelling a stick pointer returns that stick to neutral", async () => {
  const harness = createHarness();
  await settle();

  harness.leftStick.dispatch("pointerdown", { pointerId: 20, clientX: 168 });
  await settle();
  assert.equal(stateRequests(harness).at(-1).joystick.left_x, 255);

  harness.leftStick.dispatch("pointercancel", { pointerId: 20 });
  await settle();
  assert.equal(stateRequests(harness).at(-1).joystick.left_x, 128);
  assert.equal(stateRequests(harness).at(-1).joystick.left_y, 128);
});

test("a cancelled touchpad gesture does not become a tap-to-click", async () => {
  const harness = createHarness();
  await settle();
  harness.mouseTab.dispatch("click");
  await settle();

  harness.touchpad.dispatch("pointerdown", { pointerId: 30 });
  harness.touchpad.dispatch("pointercancel", { pointerId: 30 });
  await settle();

  assert.equal(stateRequests(harness).at(-1).mouse.left, 0);
});

test("two-finger touchpad movement sends mouse scroll input", async () => {
  const harness = createHarness();
  await settle();
  harness.mouseTab.dispatch("click");
  await settle();

  harness.touchpad.dispatch("pointerdown", { pointerId: 31, clientX: 100, clientY: 100 });
  harness.touchpad.dispatch("pointerdown", { pointerId: 32, clientX: 110, clientY: 100 });
  harness.touchpad.dispatch("pointermove", { pointerId: 32, clientX: 110, clientY: 128 });
  for (let i = 0; i < 10; i += 1) harness.tickFrame();
  await settle();

  assert.equal(stateRequests(harness).at(-1).mode, "mouse");
  assert.equal(stateRequests(harness).at(-1).mouse.scroll, -1);
});

test("keyboard arrows operate and recenter a focused stick", async () => {
  const harness = createHarness();
  await settle();

  harness.leftStick.dispatch("keydown", { key: "ArrowRight" });
  await settle();
  assert.equal(stateRequests(harness).at(-1).joystick.left_x, 255);

  harness.leftStick.dispatch("keyup", { key: "ArrowRight" });
  await settle();
  assert.equal(stateRequests(harness).at(-1).joystick.left_x, 128);
});

test("visibility loss and a failed connection request clear held input", async () => {
  const harness = createHarness();
  await settle();
  harness.leftStick.dispatch("pointerdown", { pointerId: 40, clientX: 168 });
  await settle();

  harness.document.hidden = true;
  harness.document.dispatch("visibilitychange");
  await settle();
  assert.equal(stateRequests(harness).at(-1).joystick.left_x, 128);

  harness.document.hidden = false;
  harness.leftStick.dispatch("pointerdown", { pointerId: 42, clientX: 168 });
  await settle();
  assert.equal(stateRequests(harness).at(-1).joystick.left_x, 255);
  harness.leftStick.dispatch("pointercancel", { pointerId: 42 });
  await settle();

  harness.setFailNextState();
  harness.gamepadButton.dispatch("pointerdown", { pointerId: 41 });
  await settle();
  assert.ok(harness.calls.some(({ url }) => url === "/api/disconnect"));
  assert.equal(harness.sessionValues.has("ib.web.token"), false);
  assert.equal(harness.gamepadButton.classList.contains("pressed"), false);
});
