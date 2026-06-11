import { App } from "./ui/app.js";

const root = document.getElementById("app");
const status = document.getElementById("status");
if (!root || !status) {
  throw new Error("Missing #app or #status element");
}

const app = new App(root, status);
void app.init();
