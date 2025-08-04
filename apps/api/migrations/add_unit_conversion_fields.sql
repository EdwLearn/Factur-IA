-- 1. Add original unit fields to invoice_line_items
ALTER TABLE invoice_line_items 
ADD COLUMN IF NOT EXISTS original_quantity NUMERIC(15,4),
ADD COLUMN IF NOT EXISTS original_unit VARCHAR(20),
ADD COLUMN IF NOT EXISTS unit_multiplier NUMERIC(10,2) DEFAULT 1;

-- 2. Add additional fields for tracking
ALTER TABLE invoice_line_items
ADD COLUMN IF NOT EXISTS item_number INTEGER,
ADD COLUMN IF NOT EXISTS enhancement_applied VARCHAR(100);

-- 3. Update existing records to avoid NULLs
UPDATE invoice_line_items 
SET 
    original_quantity = quantity,
    original_unit = COALESCE(unit_measure, 'UND'),
    unit_multiplier = 1
WHERE original_quantity IS NULL;

-- 4. Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_invoice_line_items_original_unit 
ON invoice_line_items(original_unit);

CREATE INDEX IF NOT EXISTS idx_invoice_line_items_unit_multiplier 
ON invoice_line_items(unit_multiplier);

CREATE INDEX IF NOT EXISTS idx_invoice_line_items_item_number 
ON invoice_line_items(item_number);

-- 5. Add comments for documentation
COMMENT ON COLUMN invoice_line_items.original_quantity IS 'Cantidad original antes de conversión a piezas';
COMMENT ON COLUMN invoice_line_items.original_unit IS 'Unidad original (DOC, PAR, etc.) antes de conversión';
COMMENT ON COLUMN invoice_line_items.unit_multiplier IS 'Multiplicador usado para conversión (ej: DOC=12, PAR=2)';
COMMENT ON COLUMN invoice_line_items.item_number IS 'Número de línea del item en la factura';
COMMENT ON COLUMN invoice_line_items.enhancement_applied IS 'Tipo de mejora aplicada por el sistema';

-- 6. Create view for queries with original and converted information
CREATE OR REPLACE VIEW invoice_line_items_enhanced AS
SELECT 
    id,
    invoice_id,
    item_number,
    product_code,
    description,
    reference,
    
    -- Original quantities and units
    original_quantity,
    original_unit,
    
    -- Converted quantities and units
    quantity as converted_quantity,
    unit_measure as converted_unit,
    unit_multiplier,
    
    -- Prices and totals
    unit_price,
    subtotal,
    sale_price,
    markup_percentage,
    is_priced,
    
    -- Metadata
    enhancement_applied,
    
    -- Useful calculations
    CASE 
        WHEN unit_multiplier > 1 
        THEN CONCAT(original_quantity, ' ', original_unit, ' → ', quantity, ' PCS')
        ELSE CONCAT(quantity, ' ', COALESCE(unit_measure, 'UND'))
    END as quantity_display,
    
    CASE 
        WHEN unit_multiplier > 1 
        THEN true 
        ELSE false 
    END as was_unit_converted

FROM invoice_line_items;

-- 7. Create function to get conversion summary by invoice
CREATE OR REPLACE FUNCTION get_invoice_conversion_summary(invoice_uuid UUID)
RETURNS TABLE (
    total_items BIGINT,
    items_with_conversions BIGINT,
    conversion_types TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_items,
        COUNT(*) FILTER (WHERE unit_multiplier > 1) as items_with_conversions,
        ARRAY_AGG(DISTINCT original_unit) FILTER (WHERE unit_multiplier > 1) as conversion_types
    FROM invoice_line_items 
    WHERE invoice_id = invoice_uuid;
END;
$$ LANGUAGE plpgsql;

-- Example usage:
-- SELECT * FROM get_invoice_conversion_summary('6f0c2b9a-52ed-4a8a-8eea-96ff8f739bef');

-- 8. Create a conversion audit function
CREATE OR REPLACE FUNCTION audit_unit_conversions()
RETURNS TABLE (
    invoice_id UUID,
    product_code VARCHAR,
    original_qty NUMERIC,
    original_unit VARCHAR,
    converted_qty NUMERIC,
    multiplier NUMERIC,
    enhancement_type VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ili.invoice_id,
        ili.product_code,
        ili.original_quantity,
        ili.original_unit,
        ili.quantity,
        ili.unit_multiplier,
        ili.enhancement_applied
    FROM invoice_line_items ili
    WHERE ili.unit_multiplier > 1
    ORDER BY ili.unit_multiplier DESC, ili.original_unit;
END;
$$ LANGUAGE plpgsql;

-- Example of use:
-- SELECT * FROM audit_unit_conversions() LIMIT 10;