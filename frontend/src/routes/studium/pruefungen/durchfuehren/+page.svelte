<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { ApiError, callPluginTool } from '$lib/api';
	import { ChatError } from '$lib/chat';
	import {
		ExamError, PLUGIN, gradeLocally, gradeWithModel, kindLabel, selfRatings,
		type Attempt, type Exam, type Grading, type Mode
	} from '$lib/exams';

	let exam = $state<Exam | null>(null);
	let attempt = $state<Attempt | null>(null);
	let mode: Mode = $state('schreiben');
	let index = $state(0);
	let answers: Record<number, string> = $state({});
	let revealed = $state(false);
	let loaded = $state(false);
	let busy = $state(false);
	let grading = $state(false);
	let error: string | null = $state(null);

	let question = $derived(exam?.questions[index] ?? null);
	let last = $derived(exam !== null && index === exam.questions.length - 1);

	function describe(e: unknown): string {
		if (e instanceof ApiError || e instanceof ChatError || e instanceof ExamError) return e.message;
		return 'Der Kern ist nicht erreichbar.';
	}

	onMount(async () => {
		const examId = Number(page.url.searchParams.get('exam'));
		mode = page.url.searchParams.get('mode') === 'abfrage' ? 'abfrage' : 'schreiben';
		try {
			exam = await callPluginTool<Exam>(PLUGIN, 'get_exam', { exam_id: examId });
			attempt = await callPluginTool<Attempt>(PLUGIN, 'start_attempt', { exam_id: examId, mode });
		} catch (e) {
			error = describe(e);
		} finally {
			loaded = true;
		}
	});

	async function rate(value: number) {
		if (!attempt || !question || busy) return;
		busy = true;
		error = null;
		try {
			await callPluginTool(PLUGIN, 'save_answer', {
				attempt_id: attempt.id, question_id: question.id, self_rating: value
			});
			await next();
		} catch (e) {
			error = describe(e);
		} finally {
			busy = false;
		}
	}

	async function saveWritten(): Promise<boolean> {
		if (!attempt || !question) return false;
		try {
			await callPluginTool(PLUGIN, 'save_answer', {
				attempt_id: attempt.id, question_id: question.id, answer_text: answers[question.id] ?? ''
			});
			return true;
		} catch (e) {
			error = describe(e);
			return false;
		}
	}

	async function next() {
		if (!attempt || !exam) return;
		if (mode === 'schreiben' && !(await saveWritten())) return;
		if (!last) {
			index += 1;
			revealed = false;
			return;
		}
		if (mode === 'schreiben') await gradeAll();
		else await goto(`/studium/pruefungen/ergebnis?attempt=${attempt.id}`);
	}

	async function back() {
		if (busy || index === 0) return;
		if (mode === 'schreiben') await saveWritten();
		index -= 1;
	}

	/** Multiple choice is graded locally; everything else by the Lern-Coach. */
	async function gradeAll() {
		if (!attempt || !exam) return;
		const id = attempt.id;
		grading = true;
		error = null;
		const save = (gradings: Grading[]) => callPluginTool(PLUGIN, 'save_grading', { attempt_id: id, gradings });
		try {
			const local: Grading[] = [];
			const remote = exam.questions.filter((q) => {
				const text = answers[q.id] ?? '';
				const result = text.trim() === '' ? { question_id: q.id, points: 0, feedback: 'Keine Antwort.' } : gradeLocally(q, text);
				if (result) local.push(result);
				return result === null;
			});
			if (local.length > 0) await save(local);
			if (remote.length > 0) {
				await gradeWithModel(remote, new Map(Object.entries(answers).map(([k, v]) => [Number(k), v])), async (g) => void (await save(g)));
			}
		} catch (e) {
			error = `${describe(e)} Die Antworten sind gespeichert; die Bewertung kannst du im Ergebnis erneut starten.`;
		}
		await goto(`/studium/pruefungen/ergebnis?attempt=${id}`);
	}
</script>

<h2>{exam?.title ?? 'Prüfung'} – {mode === 'schreiben' ? 'Schreiben' : 'Abfragen'}</h2>
<p><a href="/studium/pruefungen">Abbrechen</a></p>

{#if error}<p role="alert" class="error">{error}</p>{/if}

{#if !loaded}
	<p>Lade …</p>
{:else if grading}
	<p role="status">Der Lern-Coach bewertet deine Antworten …</p>
{:else if exam && question}
	<p class="muted">Frage {index + 1} von {exam.questions.length} · {kindLabel[question.kind]}{question.topic ? ` · ${question.topic}` : ''} · {question.points} Punkte</p>
	<section class="card">
		<p class="text">{question.prompt}</p>

		{#if mode === 'schreiben'}
			{#if question.kind === 'mc'}
				{#each question.options as option (option)}
					<label class="row">
						<input type="radio" name="option" value={option} bind:group={answers[question.id]} style="width:auto" />
						{option}
					</label>
				{/each}
			{:else}
				<label>
					Deine Antwort
					<textarea bind:value={answers[question.id]} rows={question.kind === 'calc' ? 8 : 6} maxlength="4000"></textarea>
				</label>
			{/if}
		{:else}
			{#if question.options.length > 0}
				<ul>{#each question.options as option (option)}<li>{option}</li>{/each}</ul>
			{/if}
			{#if revealed}
				<hr />
				<p class="text"><strong>Musterlösung:</strong> {question.model_answer}</p>
				{#if question.source_citation}<small class="muted">{question.source_citation}</small>{/if}
			{/if}
		{/if}
	</section>

	{#if mode === 'schreiben'}
		<div class="row">
			<button type="button" onclick={back} disabled={index === 0 || busy}>Zurück</button>
			<button type="button" class="primary" onclick={next} disabled={busy}>{last ? 'Abgeben und bewerten' : 'Weiter'}</button>
		</div>
	{:else if !revealed}
		<button type="button" class="primary" onclick={() => (revealed = true)}>Antwort zeigen</button>
	{:else}
		<div class="row">
			<span>Wie gut wusstest du es?</span>
			{#each selfRatings as r (r.value)}
				<button type="button" onclick={() => rate(r.value)} disabled={busy}>{r.label}</button>
			{/each}
		</div>
	{/if}
{:else if loaded && !error}
	<p>Diese Prüfung hat keine Fragen.</p>
{/if}

<style>
	.card {
		background: #fff;
		border: 1px solid #ddd;
		border-radius: 8px;
		padding: 1rem 1.25rem;
		margin: 0.75rem 0;
		max-width: 44rem;
	}
	.text {
		white-space: pre-wrap;
		margin: 0.25rem 0;
	}
</style>
