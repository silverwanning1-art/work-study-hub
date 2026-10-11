<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { ApiError, callPluginTool } from '$lib/api';
	import { ChatError } from '$lib/chat';
	import {
		ExamError, PLUGIN, formatPoints, gradeLocally, gradeWithModel, percent, weakTopics,
		type Attempt, type Exam, type Grading
	} from '$lib/exams';

	let attempt = $state<Attempt | null>(null);
	let exam = $state<Exam | null>(null);
	let loaded = $state(false);
	let busy = $state(false);
	let error: string | null = $state(null);

	let weak = $derived(attempt ? weakTopics(attempt.by_topic) : []);
	let ungraded = $derived(
		attempt && exam && attempt.mode === 'schreiben'
			? exam.questions.filter((q) => {
					const a = attempt!.answers.find((x) => x.question_id === q.id);
					return a !== undefined && a.answer_text.trim() !== '' && a.ai_points === null;
				})
			: []
	);

	function describe(e: unknown): string {
		if (e instanceof ApiError || e instanceof ChatError || e instanceof ExamError) return e.message;
		return 'Der Kern ist nicht erreichbar.';
	}

	async function load() {
		const id = Number(page.url.searchParams.get('attempt'));
		try {
			attempt = await callPluginTool<Attempt>(PLUGIN, 'get_attempt', { attempt_id: id });
			exam = await callPluginTool<Exam>(PLUGIN, 'get_exam', { exam_id: attempt.exam_id });
		} catch (e) {
			error = describe(e);
		} finally {
			loaded = true;
		}
	}
	onMount(load);

	async function regrade() {
		if (!attempt || !exam || busy) return;
		busy = true;
		error = null;
		const id = attempt.id;
		const save = (gradings: Grading[]) => callPluginTool(PLUGIN, 'save_grading', { attempt_id: id, gradings });
		try {
			const texts = new Map(attempt.answers.map((a) => [a.question_id, a.answer_text]));
			const local: Grading[] = [];
			const remote = ungraded.filter((q) => {
				const result = gradeLocally(q, texts.get(q.id) ?? '');
				if (result) local.push(result);
				return result === null;
			});
			if (local.length > 0) await save(local);
			if (remote.length > 0) await gradeWithModel(remote, texts, async (g) => void (await save(g)));
			await load();
		} catch (e) {
			error = describe(e);
		} finally {
			busy = false;
		}
	}

	const answerFor = (id: number) => attempt?.answers.find((a) => a.question_id === id);
</script>

<h2>Ergebnis</h2>
<p><a href="/studium/pruefungen">Zurück zu den Prüfungen</a></p>

{#if error}<p role="alert" class="error">{error}</p>{/if}

{#if !loaded}
	<p>Lade …</p>
{:else if attempt && exam}
	<h3>{exam.title}</h3>
	<p>
		<strong>{formatPoints(attempt.scored_points)} von {attempt.possible_points} Punkten</strong>
		({percent(attempt.scored_points, attempt.possible_points)} %) · {attempt.mode === 'schreiben' ? 'geschrieben' : 'abgefragt'} · {attempt.answered_count} von {exam.questions.length} Fragen beantwortet
	</p>

	{#if ungraded.length > 0}
		<p class="error">Für {ungraded.length} Antworten fehlt die Bewertung.</p>
		<button type="button" onclick={regrade} disabled={busy}>{busy ? 'Bewerte …' : 'Bewertung starten'}</button>
	{/if}

	<h3>Punkte je Thema</h3>
	<table class="list">
		<thead><tr><th>Thema</th><th class="num">Punkte</th><th class="num">Anteil</th></tr></thead>
		<tbody>
			{#each attempt.by_topic as t (t.topic)}
				<tr>
					<td>{t.topic}</td>
					<td class="num">{formatPoints(t.scored)} / {t.possible}</td>
					<td class="num">{percent(t.scored, t.possible)} %</td>
				</tr>
			{/each}
		</tbody>
	</table>

	{#if weak.length > 0}
		<h3>Schwache Themen</h3>
		<ul>
			{#each weak as t (t.topic)}
				<li>
					{t.topic} ({percent(t.scored, t.possible)} %)
					– <a href={`/studium/karteikarten?topic=${encodeURIComponent(t.topic)}`}>Karteikarten dazu erzeugen</a>
				</li>
			{/each}
		</ul>
	{/if}

	<h3>Aufgaben im Detail</h3>
	{#each exam.questions as q (q.id)}
		{@const a = answerFor(q.id)}
		<fieldset>
			<legend>Frage {q.position}{q.topic ? ` · ${q.topic}` : ''} · {a?.points !== null && a?.points !== undefined ? formatPoints(a.points) : '–'} / {q.points} Punkte</legend>
			<p class="text">{q.prompt}</p>
			{#if a && a.answer_text}<p class="text"><strong>Deine Antwort:</strong> {a.answer_text}</p>{/if}
			{#if a && a.ai_feedback}<p class="text"><strong>Feedback:</strong> {a.ai_feedback}</p>{/if}
			<p class="text"><strong>Musterlösung:</strong> {q.model_answer}</p>
			{#if q.source_citation}<small class="muted">{q.source_citation}</small>{/if}
		</fieldset>
	{/each}
{/if}

<style>
	.text {
		white-space: pre-wrap;
		margin: 0.25rem 0;
	}
</style>
