/**
 * TypeScript type definitions for API responses.
 *
 * These types match the Pydantic models from the FastAPI backend.
 */

export interface Entity {
  text: string;
  label: string;
  count: number;
}

export interface Sentiment {
  polarity: number;
  subjectivity: number;
  label: string;
}

export interface Article {
  id: string;
  url: string;
  title: string;
  content: string;
  published_at: string;
  media_name: string;
  is_middle_east: boolean;
  collected_at: string;
}

export interface Cluster {
  id: string;
  topic_name: string;
  articles: Article[];
  media_names: string[];
  created_at: string;
}

export interface Comparison {
  media_bias_scores: Record<string, Sentiment>;
  unique_entities_by_media: Record<string, Entity[]>;
  common_entities: Entity[];
  bias_diff: number;
}

export interface Report {
  id: string;
  cluster: Cluster;
  comparison: Comparison;
  generated_at: string;
  summary: string;
}

export interface SystemStatus {
  status: string;
  last_collection: string | null;
  total_articles: number;
  total_reports: number;
}
