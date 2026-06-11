export interface ApiErrorEnvelope {
  error_kind: string;
  error_code: string;
  retryability?: string;
}
