import { describe, expect, it, vi } from 'vitest';
import {
	ExamError,
	batchesFor,
	formatPoints,
	generateExamDraft,
	gradeLocally,
	gradeWithModel,
	parseExamDraft,
	parseGradings,
	percent,
	questionsToSave,
	weakTopics,
	type Profile,
	type Question
} from './exams';

const mcQuestion = { kind: 'mc', topic: 'Lager', prompt: 'FIFO?', options: ['A', 'B'], model_answer: 'A', points: 2, source_citation: '' };
const openQuestion = { kind: 'open', topic: 'Bestand', prompt: 'Erkläre', options: [], model_answer: 'Antwort', points: 8, source_citation: '[Quelle: A.pdf, S. 1]' };
const wrap = (value: unknown) => `Entwurf\n\`\`\`json\n${JSON.stringify(value)}\n\`\`\``;

describe('parseExamDraft', () => {
	it('parses a valid draft', () => {
		const draft = parseExamDraft(wrap({ title: 'Probe', subject: 'Logistik', questions: [mcQuestion, openQuestion] }));
		expect(draft.questions).toHaveLength(2);
		expect(draft.questions[1].source_citation).toBe('[Quelle: A.pdf, S. 1]');
	});

	it.each([
		['no block', 'nur Text'],
		['broken json', '```json\n{x\n```'],
		['no questions', wrap({ questions: [] })],
		['too many', wrap({ questions: Array.from({ length: 41 }, () => openQuestion) })],
		['unknown kind', wrap({ questions: [{ ...openQuestion, kind: 'essay' }] })],
		['mc without options', wrap({ questions: [{ ...mcQuestion, options: ['A'] }] })],
		['open with options', wrap({ questions: [{ ...openQuestion, options: ['A', 'B'] }] })],
		['points zero', wrap({ questions: [{ ...openQuestion, points: 0 }] })],
		['points fraction', wrap({ questions: [{ ...openQuestion, points: 1.5 }] })],
		['points string', wrap({ questions: [{ ...openQuestion, points: '5' }] })],
		['empty prompt', wrap({ questions: [{ ...openQuestion, prompt: ' ' }] })],
		['question not object', wrap({ questions: ['x'] })]
	])('rejects %s', (_name, answer) => {
		expect(() => parseExamDraft(answer)).toThrow(ExamError);
	});
});

describe('generateExamDraft', () => {
	const profile: Profile = {
		id: 1, name: 'Prof. X', subject: 'Logistik', description: 'Mag Rechnen', question_style: 'kurz',
		share_mc: 40, share_open: 40, share_calc: 20, difficulty: 4, notes: ''
	};

	it('puts the profile into the request and parses the answer', async () => {
		const fetchFn = vi.fn(async () => new Response(JSON.stringify({ answer: wrap({ questions: [openQuestion] }), sources: [], tool_calls: [] }), { status: 200 })) as unknown as typeof fetch;
		const draft = await generateExamDraft(profile, '', 'Lager', 5, fetchFn);
		expect(draft.questions).toHaveLength(1);
		const body = JSON.parse(((fetchFn as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1] as RequestInit).body as string);
		const content = body.messages[0].content as string;
		expect(content).toContain('pruefung-nach-prof-profil');
		expect(content).toContain('Mag Rechnen');
		expect(content).toContain('Multiple Choice 40');
		expect(content.length).toBeLessThan(8000);
	});

	it('keeps the message under the size limit even for huge profiles', async () => {
		const fetchFn = vi.fn(async () => new Response(JSON.stringify({ answer: wrap({ questions: [openQuestion] }), sources: [], tool_calls: [] }), { status: 200 })) as unknown as typeof fetch;
		const huge = { ...profile, description: 'x'.repeat(4000), question_style: 'y'.repeat(1000), notes: 'z'.repeat(2000) };
		await generateExamDraft(huge, 's'.repeat(300), 't'.repeat(500), 10, fetchFn);
		const body = JSON.parse(((fetchFn as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1] as RequestInit).body as string);
		expect((body.messages[0].content as string).length).toBeLessThanOrEqual(8000);
	});
});

describe('questionsToSave', () => {
	it('drops unchecked and empty questions and removes the keep flag', () => {
		const result = questionsToSave([
			{ ...openQuestion, kind: 'open', keep: true, prompt: ' Frage ' },
			{ ...openQuestion, kind: 'open', keep: false },
			{ ...openQuestion, kind: 'open', keep: true, model_answer: ' ' }
		]);
		expect(result).toHaveLength(1);
		expect(result[0].prompt).toBe('Frage');
		expect('keep' in result[0]).toBe(false);
	});
});

const question = (over: Partial<Question>): Question => ({ id: 1, position: 1, ...(mcQuestion as object), ...over }) as Question;

describe('gradeLocally', () => {
	it('grades multiple choice without the model', () => {
		expect(gradeLocally(question({}), 'A')).toMatchObject({ points: 2, feedback: 'Richtig.' });
		expect(gradeLocally(question({}), 'B')).toMatchObject({ points: 0 });
		expect(gradeLocally(question({}), 'B')?.feedback).toContain('Richtig ist: A');
	});

	it('leaves other kinds and unrecognisable model answers to the model', () => {
		expect(gradeLocally(question({ kind: 'open', options: [] }), 'x')).toBeNull();
		expect(gradeLocally(question({ model_answer: 'Option A' }), 'A')).toBeNull();
	});
});

describe('parseGradings', () => {
	const max = new Map([[1, 5], [2, 3]]);

	it('rounds and limits points', () => {
		const result = parseGradings(wrap({ gradings: [{ question_id: 1, points: 9, feedback: 'ok' }, { question_id: 2, points: -2.4, feedback: '' }] }), max);
		expect(result.map((g) => g.points)).toEqual([5, 0]);
	});

	it('ignores duplicates and rejects unknown questions or bad shapes', () => {
		const duplicate = parseGradings(wrap({ gradings: [{ question_id: 1, points: 1 }, { question_id: 1, points: 5 }] }), max);
		expect(duplicate).toEqual([{ question_id: 1, points: 1, feedback: '' }]);
		expect(() => parseGradings(wrap({ gradings: [{ question_id: 9, points: 1 }] }), max)).toThrow(ExamError);
		expect(() => parseGradings(wrap({ gradings: [{ question_id: 1, points: 'viel' }] }), max)).toThrow(ExamError);
		expect(() => parseGradings(wrap({ nope: [] }), max)).toThrow(ExamError);
		expect(() => parseGradings('kein Block', max)).toThrow(ExamError);
	});
});

describe('batching and grading', () => {
	it('splits large inputs into batches under the limit', () => {
		const items = Array.from({ length: 10 }, (_, i) => ({ question_id: i, prompt: 'p'.repeat(1000), model_answer: 'm', max_points: 1, answer: 'a' }));
		const batches = batchesFor(items, 3000);
		expect(batches.flat()).toHaveLength(10);
		for (const batch of batches) expect(JSON.stringify(batch).length).toBeLessThan(3500);
		expect(batches.length).toBeGreaterThan(1);
	});

	it('grades batch by batch, ignoring gradings for questions outside the batch', async () => {
		const questions = [question({ id: 1, kind: 'open', options: [], points: 5 }), question({ id: 2, kind: 'open', options: [], points: 5 })];
		const fetchFn = vi.fn(async () => new Response(JSON.stringify({ answer: wrap({ gradings: [{ question_id: 1, points: 4, feedback: 'gut' }, { question_id: 2, points: 5, feedback: '' }] }), sources: [], tool_calls: [] }), { status: 200 })) as unknown as typeof fetch;
		const saved: number[][] = [];
		await gradeWithModel(questions, new Map([[1, 'a'], [2, 'b']]), async (g) => void saved.push(g.map((x) => x.question_id)), fetchFn);
		expect(saved).toEqual([[1, 2]]);
	});
});

describe('result helpers', () => {
	it('computes percent and formats points', () => {
		expect(percent(5, 10)).toBe(50);
		expect(percent(1, 0)).toBe(0);
		expect(formatPoints(4)).toBe('4');
		expect(formatPoints(4.5)).toBe('4,5');
	});

	it('finds weak topics, weakest first, without the placeholder topic', () => {
		const weak = weakTopics([
			{ topic: 'A', scored: 5, possible: 10 },
			{ topic: 'B', scored: 9, possible: 10 },
			{ topic: 'C', scored: 1, possible: 10 },
			{ topic: 'Ohne Thema', scored: 0, possible: 10 }
		]);
		expect(weak.map((t) => t.topic)).toEqual(['C', 'A']);
	});
});
