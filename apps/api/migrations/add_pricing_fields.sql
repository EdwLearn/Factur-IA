-- Agregar campos de pricing a invoice_line_items
ALTER TABLE invoice_line_items 
ADD COLUMN sale_price NUMERIC(15,2),
ADD COLUMN markup_percentage NUMERIC(5,2),
ADD COLUMN is_priced BOOLEAN DEFAULT FALSE;

-- Agregar campo de estado extendido a processed_invoices
ALTER TABLE processed_invoices 
ADD COLUMN pricing_status VARCHAR(50) DEFAULT 'not_required';

-- Índices para performance
CREATE INDEX idx_invoice_line_items_is_priced ON invoice_line_items(is_priced);
CREATE INDEX idx_processed_invoices_pricing_status ON processed_invoices(pricing_status);
