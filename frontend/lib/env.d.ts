namespace NodeJS {
  interface ProcessEnv {
    NEXT_BACKEND_URL: string;
    AWS_ACCESS_KEY_ID: string;
    AWS_SECRET_ACCESS_KEY: string;
    AWS_BUCKET_NAME: string;
    AWS_REGION_NAME: string;
    // Add other env variables here
  }
}