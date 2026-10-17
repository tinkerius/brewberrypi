/** The single-page UI (docs/specification/09-user-interface.md §9.1). */

import { useEffect, useState } from "preact/hooks";
import { Chart } from "./Chart";
import { fetchVersion, sendCommand } from "./api";
import { InformationModal, StopConfirmation } from "./dialogs";
import { EventStream } from "./events";
import { ConnectionIndicator, HardwareStatusPanel, PageHeader, Panel, ProcessPanel, type SendCommand } from "./panels";
import { type AppState, addReply, dismissReply, initialState, receive, setConnected } from "./state";

export function App() {
  const [state, setState] = useState<AppState>(initialState);
  const [everConnected, setEverConnected] = useState(false);
  const [confirmingStop, setConfirmingStop] = useState(false);
  const [version, setVersion] = useState<string | null>(null);
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
  // UI-001: read the version on every (re)connection; the app may have been updated in between.
  useEffect(() => {
    if (state.connected) {
      void fetchVersion().then((current) => current !== null && setVersion(current));
    }
  }, [state.connected]);

  const send: SendCommand = (command, args = {}) => {
    void sendCommand(command, args).then((reply) => setState((current) => addReply(current, reply)));
  };

  return (
    <>
      <PageHeader host={location.hostname} version={version} />
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
