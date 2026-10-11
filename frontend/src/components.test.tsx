// @vitest-environment jsdom
import { render } from "preact";
import { act } from "preact/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { InformationModal, STOP_QUESTION, StopConfirmation } from "./dialogs";
import { APP_TITLE, ConnectionIndicator, HardwareStatusPanel, ProcessPanel, type SendCommand } from "./panels";
import type { ProcessState, Recipe } from "./types";

let root: HTMLElement;

beforeEach(() => {
  root = document.createElement("div");
  document.body.append(root);
});

afterEach(() => {
  render(null, root);
  root.remove();
});

function show(element: preact.ComponentChild) {
  act(() => render(element, root));
}

function buttons(): HTMLButtonElement[] {
  return [...root.querySelectorAll("button")];
}

function button(label: string): HTMLButtonElement {
  const found = buttons().find((b) => b.textContent === label);
  if (found === undefined) {
    throw new Error(`no button ${label}`);
  }
  return found;
}

const RECIPES: Recipe[] = [
  { id: "ZORA", name: "München 12.6 - SUD1:ZORA" },
  { id: "TEST", name: "Test Process" },
];

const RUNNING: ProcessState = {
  processid: "TEST",
  processname: "Test Process",
  state: "Running",
  goals: [
    { name: "Heat Up", description: "Heat up mash to 25.0 degrees (C).", status: "Done", statuspercent: 100, statusmessage: "100%" },
    {
      name: "Iodine Test",
      description: "Now it's your job to do the iodine test.\nRest at 25.0 degrees (C) for 1min.",
      status: "Active",
      statuspercent: 40,
      statusmessage: "00:36 left",
      activeRequest: { message: "Iodine test successfull?", options: ["Yes", "No"] },
    },
    { name: "Lautering", description: "Now it's your job to lauter.", status: "Waiting", statuspercent: 0, statusmessage: "0%" },
  ],
};

function processPanel(process: ProcessState | null, connected = true, recipes: Recipe[] | null = RECIPES) {
  const send = vi.fn<SendCommand>();
  const onStop = vi.fn();
  show(<ProcessPanel process={process} recipes={recipes} connected={connected} send={send} onStop={onStop} />);
  return { send, onStop };
}

describe("page", () => {
  it("uses the title from the specification", () => {
    expect(APP_TITLE).toBe("Brewberry Pi");
  });
});

describe("Hardware Status panel", () => {
  it("UI-010 UI-011 shows the values and the engine state", () => {
    show(<HardwareStatusPanel hardware={{ temperature: 62.5, pumpstatus: true, heatingstatus: 0.5 }} state="Running" stale={false} />);
    expect(root.textContent).toContain("Temperature:62.5°C");
    expect(root.textContent).toContain("Pump:on");
    expect(root.textContent).toContain("Heating:50%");
    expect(root.textContent).toContain("Process:Running");
  });

  it("AC-005 shows Sensor error", () => {
    show(<HardwareStatusPanel hardware={{ temperature: null, pumpstatus: true, heatingstatus: 0 }} state="Running" stale={false} />);
    expect(root.querySelector(".sensor-error")?.textContent).toBe("Sensor error");
  });

  it("UI-061 marks values as stale while disconnected", () => {
    show(<HardwareStatusPanel hardware={null} state={undefined} stale={true} />);
    expect(root.querySelector(".panel")?.classList.contains("stale")).toBe(true);
    expect(root.textContent).toContain("Temperature:--");
  });
});

describe("Brewing Process panel", () => {
  it("UI-030 shows the process name and one item per goal in order", () => {
    processPanel(RUNNING);
    expect(root.querySelector(".process-name")?.textContent).toBe("Test Process");
    expect([...root.querySelectorAll(".goal h3")].map((h) => h.textContent)).toEqual(["Heat Up", "Iodine Test", "Lautering"]);
    expect([...root.querySelectorAll(".goal .badge")].map((b) => b.textContent)).toEqual(["Done", "Active", "Waiting"]);
  });

  it("AC-075 active goal has a progress bar with the status message; done goals are green", () => {
    processPanel(RUNNING);
    const [done, active, waiting] = root.querySelectorAll<HTMLElement>(".goal");
    expect(done.classList.contains("goal-done")).toBe(true);
    expect(active.classList.contains("goal-active")).toBe(true);
    expect(waiting.className).toBe("goal");
    expect(root.querySelectorAll(".progress")).toHaveLength(1);
    expect(active.querySelector<HTMLElement>(".progress-bar")?.style.width).toBe("40%");
    expect(active.querySelector(".progress-label")?.textContent).toBe("00:36 left");
  });

  it("AC-075 UI-032 request buttons send the exact option text", () => {
    const { send } = processPanel(RUNNING);
    expect(root.querySelector(".request p")?.textContent).toBe("Iodine test successfull?");
    act(() => button("No").click());
    expect(send).toHaveBeenCalledWith("respond", { response: "No" });
  });

  it("FIX-24 renders line breaks in descriptions", () => {
    processPanel(RUNNING);
    const description = root.querySelectorAll(".goal .description")[1];
    expect(description.querySelectorAll("br")).toHaveLength(1);
  });

  it("UI-030 shows nothing for no process", () => {
    processPanel({ state: "NoProcess" });
    expect(root.querySelector(".process-name")).toBeNull();
    expect(root.querySelectorAll(".goal")).toHaveLength(0);
  });

  it("UI-040 loads the selected recipe", () => {
    const { send } = processPanel({ state: "NoProcess" });
    const select = root.querySelector("select") as HTMLSelectElement;
    expect([...select.options].map((o) => o.textContent)).toEqual(["Load Process", "München 12.6 - SUD1:ZORA", "Test Process"]);
    act(() => {
      select.value = "ZORA";
      select.dispatchEvent(new Event("change"));
    });
    expect(send).toHaveBeenCalledWith("load", { recipe: "ZORA" });
  });

  it("UI-040 shows loading… before the recipe list arrives", () => {
    processPanel({ state: "NoProcess" }, true, null);
    const select = root.querySelector("select") as HTMLSelectElement;
    expect(select.disabled).toBe(true);
    expect(select.options[0].textContent).toBe("loading…");
  });

  it("UI-041 UI-042 buttons send their commands and are enabled per engine state", () => {
    const { send, onStop } = processPanel({ ...RUNNING, state: "Running" });
    expect(button("Start Process").disabled).toBe(true);
    expect(button("Unload Process").disabled).toBe(true);
    expect((root.querySelector("select") as HTMLSelectElement).disabled).toBe(true);
    act(() => button("Pause Process").click());
    expect(send).toHaveBeenCalledWith("pause");
    act(() => button("Stop Process").click());
    expect(onStop).toHaveBeenCalled(); // UI-043: asks first

    const loaded = processPanel({ ...RUNNING, state: "Loaded" });
    act(() => button("Start Process").click());
    expect(loaded.send).toHaveBeenCalledWith("start");
    act(() => button("Unload Process").click());
    expect(loaded.send).toHaveBeenCalledWith("unload");
    expect(button("Pause Process").disabled).toBe(true);
    expect(button("Stop Process").disabled).toBe(true);
  });

  it("AC-077 UI-061 disables all commands while disconnected", () => {
    processPanel(RUNNING, false);
    expect(buttons().every((b) => b.disabled)).toBe(true);
    expect((root.querySelector("select") as HTMLSelectElement).disabled).toBe(true);
  });
});

describe("dialogs", () => {
  it("AC-076 shows the reply message in the Information modal; Confirm closes it", () => {
    const onConfirm = vi.fn();
    show(<InformationModal reply={{ command: "load", success: true, message: "Process Test Process (TEST) loaded." }} onConfirm={onConfirm} />);
    expect(root.querySelector(".modal-title")?.textContent).toBe("Information");
    expect(root.querySelector(".modal-body")?.textContent).toBe("Process Test Process (TEST) loaded.");
    act(() => button("Confirm").click());
    expect(onConfirm).toHaveBeenCalled();
    show(<InformationModal reply={undefined} onConfirm={onConfirm} />);
    expect(root.querySelector(".modal")).toBeNull();
  });

  it("UI-043 asks before stopping", () => {
    const onStop = vi.fn();
    const onCancel = vi.fn();
    show(<StopConfirmation open={true} onCancel={onCancel} onStop={onStop} />);
    expect(root.textContent).toContain(STOP_QUESTION);
    expect(STOP_QUESTION).toBe("Stop the running process? Heating and pump will be switched off.");
    act(() => button("Cancel").click());
    expect(onCancel).toHaveBeenCalled();
    act(() => button("Stop Process").click());
    expect(onStop).toHaveBeenCalled();
  });
});

describe("connection indicator", () => {
  it("AC-077 UI-060 shows disconnected — reconnecting… after losing the connection", () => {
    show(<ConnectionIndicator connected={false} everConnected={true} />);
    expect(root.querySelector('[role="status"]')?.textContent).toBe("disconnected — reconnecting…");
    show(<ConnectionIndicator connected={true} everConnected={true} />);
    expect(root.querySelector('[role="status"]')).toBeNull();
  });
});
