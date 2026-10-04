<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		let target = '/arbeit';
		try {
			if (localStorage.getItem('hub.workspace') === 'studium') target = '/studium';
		} catch {
			// Storage can be blocked; the default is fine.
		}
		void goto(target, { replaceState: true });
	});
</script>

<p>Lade …</p>
