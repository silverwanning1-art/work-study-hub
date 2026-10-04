export interface Profile {
	name: string;
	street: string;
	postal_code: string;
	city: string;
	country: string;
	tax_number: string;
	vat_id: string;
	email: string;
	phone: string;
	bank_name: string;
	iban: string;
	bic: string;
	tax_exemption_note: string;
	payment_terms_days: number;
}

export interface Customer {
	id: number | null;
	name: string;
	street: string;
	postal_code: string;
	city: string;
	country: string;
	vat_id: string;
	email: string;
}

export interface Project {
	id: number | null;
	customer_id: number;
	name: string;
	notes: string;
}

export interface Item {
	position: number;
	description: string;
	quantity: string;
	unit: string;
	unit_price: string;
	tax_rate_percent: number;
	net: string;
}

export interface Totals {
	net: string;
	tax_lines: { tax_rate_percent: number; net: string; tax: string }[];
	tax: string;
	gross: string;
}

export type Status = 'draft' | 'issued' | 'paid' | 'cancelled';

export interface Invoice {
	id: number;
	status: Status;
	number: string | null;
	customer_id: number;
	project_id: number | null;
	issue_date: string | null;
	service_start: string | null;
	service_end: string | null;
	note: string;
	items: Item[];
	totals: Totals;
	cancels_number: string | null;
	tax_exemption_note: string;
}

export const statusLabel: Record<Status, string> = {
	draft: 'Entwurf',
	issued: 'Offen',
	paid: 'Bezahlt',
	cancelled: 'Storniert'
};
