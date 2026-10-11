/** Modal dialogs: Information (UI-050) and the stop confirmation (UI-043). */

import type { CommandReply } from "./types";

function Modal(props: { title: string; children: preact.ComponentChildren; buttons: preact.ComponentChildren }) {
  return (
    <div class="modal-backdrop">
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <h2 id="modal-title" class="modal-title">
          {props.title}
        </h2>
        <div class="modal-body">{props.children}</div>
        <div class="modal-footer">{props.buttons}</div>
      </div>
    </div>
  );
}

/** UI-050 (Q-11 default: a modal for every reply). Shows the oldest unconfirmed reply. */
export function InformationModal(props: { reply: CommandReply | undefined; onConfirm: () => void }) {
  if (props.reply === undefined) {
    return null;
  }
  return (
    <Modal
      title="Information"
      buttons={
        <button type="button" class="btn btn-primary" onClick={props.onConfirm} autoFocus>
          Confirm
        </button>
      }
    >
      <p class={props.reply.success ? undefined : "reply-error"}>{props.reply.message}</p>
    </Modal>
  );
}

export const STOP_QUESTION = "Stop the running process? Heating and pump will be switched off.";

/** UI-043: a stopped process cannot be resumed, so stopping is confirmed first. */
export function StopConfirmation(props: { open: boolean; onCancel: () => void; onStop: () => void }) {
  if (!props.open) {
    return null;
  }
  return (
    <Modal
      title="Stop Process"
      buttons={
        <>
          <button type="button" class="btn" onClick={props.onCancel} autoFocus>
            Cancel
          </button>
          <button type="button" class="btn btn-danger" onClick={props.onStop}>
            Stop Process
          </button>
        </>
      }
    >
      <p>{STOP_QUESTION}</p>
    </Modal>
  );
}
