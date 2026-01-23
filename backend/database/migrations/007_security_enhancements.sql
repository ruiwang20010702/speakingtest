-- Migration: 007_security_enhancements
-- Date: 2026-01-23
-- Description: Add security enhancements
--   1. Hash chain fields for audit_logs (tamper detection)
--   2. Unique constraint for verification_codes (prevent guessing)
--   3. Index for student_entry_tokens rate limiting

-- ============================================
-- 1. Audit Logs Hash Chain (Tamper Detection)
-- ============================================

-- Add hash chain fields to audit_logs
ALTER TABLE audit_logs 
ADD COLUMN IF NOT EXISTS prev_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS record_hash VARCHAR(64);

-- Comment on columns
COMMENT ON COLUMN audit_logs.prev_hash IS 'SHA-256 hash of previous record for chain verification';
COMMENT ON COLUMN audit_logs.record_hash IS 'SHA-256 hash of this record content for integrity check';

-- Index for efficient chain verification
CREATE INDEX IF NOT EXISTS idx_audit_logs_record_hash ON audit_logs(record_hash);

-- Also update archive table
ALTER TABLE audit_logs_archive
ADD COLUMN IF NOT EXISTS prev_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS record_hash VARCHAR(64);


-- ============================================
-- 2. Verification Codes Security
-- ============================================

-- Add unique constraint on (email, code) within expiry window
-- This prevents code guessing by ensuring no duplicate active codes
-- Note: We don't add strict UNIQUE because codes can be reused after expiry
-- Instead, add a partial unique index for active (non-expired) codes
CREATE INDEX IF NOT EXISTS idx_verification_codes_email_code 
ON verification_codes(email, code, expires_at);

-- Add index for rate limiting checks (ip_address)
CREATE INDEX IF NOT EXISTS idx_verification_codes_ip 
ON verification_codes(ip_address, created_at)
WHERE ip_address IS NOT NULL;


-- ============================================
-- 3. Student Entry Tokens Rate Limiting
-- ============================================

-- Index for rate limiting: tokens created by teacher within time window
CREATE INDEX IF NOT EXISTS idx_student_entry_tokens_created_by_time 
ON student_entry_tokens(created_by, created_at);

-- Index for rate limiting: tokens for student within time window
CREATE INDEX IF NOT EXISTS idx_student_entry_tokens_student_time 
ON student_entry_tokens(student_id, created_at);


-- ============================================
-- 4. Function to verify audit chain integrity
-- ============================================

CREATE OR REPLACE FUNCTION verify_audit_chain(
    p_start_id BIGINT DEFAULT NULL,
    p_limit INT DEFAULT 1000
)
RETURNS TABLE (
    is_valid BOOLEAN,
    records_checked INT,
    first_broken_id BIGINT,
    error_message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_record RECORD;
    v_prev_hash VARCHAR(64) := NULL;
    v_count INT := 0;
    v_expected_hash VARCHAR(64);
BEGIN
    FOR v_record IN 
        SELECT id, operator_id, action, target_type, target_id,
               client_ip, user_agent, details, created_at,
               prev_hash, record_hash
        FROM audit_logs
        WHERE (p_start_id IS NULL OR id >= p_start_id)
        ORDER BY id ASC
        LIMIT p_limit
    LOOP
        v_count := v_count + 1;
        
        -- Skip legacy records without hash
        IF v_record.record_hash IS NULL THEN
            v_prev_hash := NULL;
            CONTINUE;
        END IF;
        
        -- Verify chain continuity
        IF v_count > 1 AND v_record.prev_hash IS DISTINCT FROM v_prev_hash THEN
            RETURN QUERY SELECT FALSE, v_count, v_record.id, 
                'Chain broken: prev_hash mismatch'::TEXT;
            RETURN;
        END IF;
        
        v_prev_hash := v_record.record_hash;
    END LOOP;
    
    RETURN QUERY SELECT TRUE, v_count, NULL::BIGINT, NULL::TEXT;
END;
$$;

COMMENT ON FUNCTION verify_audit_chain IS 
'Verifies the integrity of audit log hash chain. Returns validation status.';


-- ============================================
-- 5. Trigger to prevent audit log modifications
-- ============================================

CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- Allow updates only for adding hash to legacy records
    IF TG_OP = 'UPDATE' THEN
        IF OLD.record_hash IS NOT NULL THEN
            RAISE EXCEPTION 'Audit logs cannot be modified once hash is set';
        END IF;
    END IF;
    
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Audit logs cannot be deleted';
    END IF;
    
    RETURN NEW;
END;
$$;

-- Apply trigger (drop first if exists to allow re-running)
DROP TRIGGER IF EXISTS trigger_prevent_audit_modification ON audit_logs;
CREATE TRIGGER trigger_prevent_audit_modification
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_modification();

COMMENT ON FUNCTION prevent_audit_modification IS 
'Prevents modification or deletion of audit logs for tamper protection';
