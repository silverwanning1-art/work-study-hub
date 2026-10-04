import { describe, expect, it } from 'vitest';
import { formatDate, formatEuro, parseDecimal, toInputDecimal } from './format';

describe('formatEuro', () => {
	it('formats with German separators', () => {
		expect(formatEuro('238.00')).toBe('238,00 €');
		expect(formatEuro('1234567.5')).toBe('1.234.567,50 €');
		expect(formatEuro('-0.05')).toBe('-0,05 €');
	});
});

describe('formatDate', () => {
	it('formats ISO dates and tolerates empty values', () => {
		expect(formatDate('2026-11-03')).toBe('03.11.2026');
		expect(formatDate(null)).toBe('');
		expect(formatDate('')).toBe('');
	});
});

describe('parseDecimal', () => {
	it('reads German input', () => {
		expect(parseDecimal('2,5')).toBe('2.5');
		expect(parseDecimal('1.250,5')).toBe('1250.5');
		expect(parseDecimal(' 80 ')).toBe('80');
		expect(parseDecimal('80,00')).toBe('80.00');
	});

	it('reads English decimals and thousands groups', () => {
		expect(parseDecimal('2.5')).toBe('2.5');
		expect(parseDecimal('1.250')).toBe('1250');
	});

	it('rejects text that is not a number', () => {
		expect(parseDecimal('')).toBeNull();
		expect(parseDecimal('abc')).toBeNull();
		expect(parseDecimal('1,2,3')).toBeNull();
		expect(parseDecimal('12 €')).toBeNull();
	});
});

describe('toInputDecimal', () => {
	it('swaps the decimal point for a comma', () => {
		expect(toInputDecimal('2.5')).toBe('2,5');
	});
});
