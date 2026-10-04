/** Format a decimal string such as "1234.5" or "-0.05" as German euro text. */
export function formatEuro(decimal: string): string {
	const negative = decimal.startsWith('-');
	const [whole, fraction = ''] = decimal.replace('-', '').split('.');
	const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
	return `${negative ? '-' : ''}${grouped},${fraction.padEnd(2, '0').slice(0, 2)} €`;
}

/** Format an ISO date (2026-11-03) as 03.11.2026; empty or missing gives an empty string. */
export function formatDate(iso: string | null | undefined): string {
	if (!iso) return '';
	const [year, month, day] = iso.split('-');
	return `${day}.${month}.${year}`;
}

/**
 * Turn German input ("1.250,5" or "2,5") into the decimal string the API expects ("1250.5").
 * Returns null when the text is not a plain number.
 */
export function parseDecimal(input: string): string | null {
	const text = input.trim().replace(/\s/g, '');
	if (!/^-?\d{1,3}(\.\d{3})*(,\d+)?$|^-?\d+(,\d+)?$|^-?\d+\.\d+$/.test(text)) return null;
	if (text.includes(',')) return text.replace(/\./g, '').replace(',', '.');
	// Without a comma, "1.250" is a German thousands group, while "2.5" is an English decimal.
	if (/^-?\d{1,3}(\.\d{3})+$/.test(text)) return text.replace(/\./g, '');
	return text;
}

/** Show an API decimal ("2.5") the way users type it ("2,5"). */
export function toInputDecimal(decimal: string): string {
	return decimal.replace('.', ',');
}
