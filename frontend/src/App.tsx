/** The single-page UI (docs/specification/09-user-interface.md §9.1). */

import { useEffect, useRef, useState } from "preact/hooks";
import { Chart } from "./Chart";
import { Connection, defaultUrl } from "./connection";
import { InformationModal, StopConfirmation } from "./dialogs";
import { APP_TITLE, ConnectionIndicator, HardwareStatusPanel, Panel, ProcessPanel, type SendCommand } from "./panels";
import { type AppState, dismissReply, initialState, receive, setConnected } from "./state";
import { COMMAND_TOPICS } from "./types";

export function App() {
  const [state, setState] = useState<AppState>(initialState);
  const [everConnected, setEverConnected] = useState(false);
  const [confirmingStop, setConfirmingStop] = useState(false);
  const connection = useRef<Connection | null>(null);

  useEffect(() => {
    const channel = new Connection({
      url: defaultUrl(window.location),
      onMessage: (topic, payload) => setState((current) => receive(current, topic, payload)),
      onConnectedChange: (connected) => {
        setState((current) => setConnected(current, connected));
        if (connected) {
          setEverConnected(true);
        }
      },
    });
    connection.current = channel;
    channel.start();
    return () => channel.stop();
  }, []);

  const send: SendCommand = (command, payload = {}) => {
    connection.current?.send(COMMAND_TOPICS[command], payload);
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
