import * as tf from "@tensorflow/tfjs";
import * as use from "@tensorflow-models/universal-sentence-encoder";

let modelPromise: Promise<use.UniversalSentenceEncoder> | null = null;

function getModel() {
  if (!modelPromise) {
    modelPromise = use.load();
  }
  return modelPromise;
}

function cosineSimilarity(a: tf.Tensor, b: tf.Tensor): number {
  const dotProduct = tf.sum(tf.mul(a, b)).dataSync()[0];
  const normA = tf.norm(a).dataSync()[0];
  const normB = tf.norm(b).dataSync()[0];
  return normA && normB ? dotProduct / (normA * normB) : 0;
}

export interface Scholarship {
  name: string;
  provider: string;
  amount: string;
  deadline: string;
  match_score: number;
  description: string;
  url?: string;
  match_reasons: string[];
  documents_required?: string[];
  tf_similarity?: number;
  final_score?: number;
}

export async function reRankScholarships(
  profileText: string,
  scholarships: Scholarship[]
): Promise<Scholarship[]> {
  try {
    const model = await getModel();
    const texts = [profileText, ...scholarships.map((s) => `${s.name}. ${s.description}. ${s.match_reasons.join(". ")}`)];
    const embeddings = await model.embed(texts);
    const profileEmbedding = embeddings.slice([0, 0], [1, -1]);

    const rankedScholarships = scholarships.map((scholarship, i) => {
      const scholarshipEmbedding = embeddings.slice([i + 1, 0], [1, -1]);
      const similarity = cosineSimilarity(
        profileEmbedding.reshape([-1]),
        scholarshipEmbedding.reshape([-1])
      );
      const normalizedSimilarity = Math.round(((similarity + 1) / 2) * 100);
      const finalScore = Math.round(scholarship.match_score * 0.7 + normalizedSimilarity * 0.3);

      return { ...scholarship, tf_similarity: normalizedSimilarity, final_score: finalScore };
    });

    embeddings.dispose();
    profileEmbedding.dispose();

    return rankedScholarships.sort((a, b) => (b.final_score ?? 0) - (a.final_score ?? 0));
  } catch (error) {
    console.error("TensorFlow.js re-ranking failed, using AI scores only:", error);
    return scholarships.map((s) => ({ ...s, final_score: s.match_score }));
  }
}
