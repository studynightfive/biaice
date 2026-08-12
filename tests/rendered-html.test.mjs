import assert from "node:assert/strict";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("renders the data-driven bidding strategy demo", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<html[^>]*lang="zh-CN"/i);
  assert.match(html, /标策 AI｜资料驱动的多智能体投标策略/);
  assert.match(html, /资料先画像，智能体再对抗/);
  assert.match(html, /竞争公司资料与历史投标信息/);
  assert.match(html, /生成竞争者画像/);
  assert.match(html, /多方案决策/);
  assert.match(html, /自动生成稳妥中标、利润最大、均衡和利润保护方案/);
});

test("keeps rule and data boundaries visible", async () => {
  const response = await render();
  const html = await response.text();

  assert.match(html, /评分项、权重与公式来自当前项目/);
  assert.match(html, /仅使用公开信息、已获授权或企业合法持有的数据/);
  assert.match(html, /提高可解释决策质量，不承诺中标/);
  assert.doesNotMatch(html, /保证中标/);
  assert.doesNotMatch(html, /Your site is taking shape|codex-preview|Building your site/);
});
