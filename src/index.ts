import { Container, getRandom } from "@cloudflare/containers";

/** Number of container instances to spread traffic across (<= max_instances in wrangler.jsonc). */
const INSTANCE_COUNT = 1;

export class TokenizerContainer extends Container<Env> {
  defaultPort = 8080;
  sleepAfter = "10m";
  envVars = {
    INSTALLED_PACKS: "thai",
    AUTO_ROUTING: "true",
    DEFAULT_TOKENIZER: "whitespace",
  };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const container = await getRandom(env.TOKENIZER, INSTANCE_COUNT);
    return container.fetch(request);
  },
} satisfies ExportedHandler<Env>;
