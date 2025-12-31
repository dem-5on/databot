CREATE TABLE IF NOT EXISTS health_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL, -- 'healthy', 'degraded', 'down'
    latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster querying of recent logs
CREATE INDEX IF NOT EXISTS idx_health_logs_service_created_at 
ON health_logs (service_name, created_at DESC);

-- quyXcTNHMTmvZHYraCoLXSdIbrq8gazGZzCdAIO902ZRjOVpQtROmvO4vuFteA3v