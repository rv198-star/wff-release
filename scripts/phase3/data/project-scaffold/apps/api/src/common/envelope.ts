export interface ApiEnvelope<TData> {
  trace_id: string;
  request_id?: string;
  data: TData;
  meta?: Record<string, unknown>;
}
