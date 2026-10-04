<script lang="ts">
	let {
		open,
		title,
		message,
		confirmLabel,
		onconfirm,
		oncancel
	}: {
		open: boolean;
		title: string;
		message: string;
		confirmLabel: string;
		onconfirm: () => void;
		oncancel: () => void;
	} = $props();

	let dialog: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) dialog.showModal();
		if (!open && dialog.open) dialog.close();
	});
</script>

<dialog bind:this={dialog} oncancel={oncancel} onclose={oncancel}>
	<h3>{title}</h3>
	<p>{message}</p>
	<div class="actions">
		<button type="button" onclick={oncancel}>Abbrechen</button>
		<button type="button" class="primary" onclick={onconfirm}>{confirmLabel}</button>
	</div>
</dialog>

<style>
	dialog {
		border: 1px solid #888;
		border-radius: 8px;
		max-width: 28rem;
	}
	.actions {
		display: flex;
		gap: 0.5rem;
		justify-content: flex-end;
	}
</style>
