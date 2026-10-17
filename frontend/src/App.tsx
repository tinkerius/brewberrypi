/** The single-page UI (docs/specification/09-user-interface.md §9.1). */

import { useEffect, useState } from "preact/hooks";
import { Chart } from "./Chart";
import { sendCommand } from "./api";
import { InformationModal, StopConfirmation } from "./dialogs";
import { EventStream } from "./events";
import { APP_TITLE, ConnectionIndicator, HardwareStatusPanel, Panel, ProcessPanel, type SendCommand } from "./panels";
import { type AppState, addReply, dismissReply, initialState, receive, setConnected } from "./state";

export function App() {
  const [state, setState] = useState<AppState>(initialState);
  const [everConnected, setEverConnected] = useState(false);
  const [confirmingStop, setConfirmingStop] = useState(false);
  useEffect(() => {
    const stream = new EventStream({
      url: "/api/events",
      onEvent: (name, data) => setState((current) => receive(current, name, data)),
      onConnectedChange: (connected) => {
        setState((current) => setConnected(current, connected));
        if (connected) {
          setEverConnected(true);
        }
      },
    });
    stream.start();
    return () => stream.stop();
  }, []);

  const send: SendCommand = (command, args = {}) => {
    void sendCommand(command, args).then((reply) => setState((current) => addReply(current, reply)));
  };

  return (
    <>
      <header class="border-b border-slate-200 bg-white dark:border-white/10 dark:bg-slate-900">
        <div class="mx-auto flex max-w-5xl items-center gap-3 px-4 py-4 sm:px-6">
          <span class="size-3 rounded-full bg-indigo-600" aria-hidden="true" />
          <h1 class="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">{APP_TITLE}</h1>
        </div>
      </header>
      <main class="mx-auto max-w-5xl space-y-6 px-4 py-6 sm:px-6">
        <ConnectionIndicator connected={state.connected} everConnected={everConnected} />
        <HardwareStatusPanel hardware={state.hardware} state={state.process?.state} stale={!state.connected} />
        <Panel title="Chart" stale={!state.connected}>
          <Chart series={state.chart} />
        </Panel>
        <ProcessPanel
          process={state.process}
          recipes={state.recipes}
          connected={state.connected}
          send={send}
          onStop={() => setConfirmingStop(true)}
        />
      </main>
      <StopConfirmation
        open={confirmingStop}
        onCancel={() => setConfirmingStop(false)}
        onStop={() => {
          setConfirmingStop(false);
          send("stop");
        }}
      />
      <InformationModal reply={state.replies[0]} onConfirm={() => setState(dismissReply)} />
    </>
  );
}
