// First: makes navigator.language valid before uPlot (imported by App) reads it.
import "./locale";
import { render } from "preact";
import { App } from "./App";
import "./styles.css";

const root = document.getElementById("app");
if (root) {
  render(<App />, root);
}
