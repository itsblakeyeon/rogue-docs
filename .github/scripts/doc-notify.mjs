import { readFileSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const THREADS_FILE = resolve(__dirname, "..", "slack-threads.json");
const CHANNEL_ID = process.env.SLACK_CHANNEL_ID;
const SLACK_TOKEN = process.env.SLACK_BOT_TOKEN;
const CHANGED_FILES = process.env.CHANGED_FILES || "";
const COMMIT_MESSAGE = process.env.COMMIT_MESSAGE || "";
const COMMIT_URL = process.env.COMMIT_URL || "";

async function slackPost(body) {
  const res = await fetch("https://slack.com/api/chat.postMessage", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${SLACK_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!data.ok) {
    throw new Error(`Slack API error: ${data.error}`);
  }
  return data;
}

// 4-프로젝트/{프로젝트명}/ 하위 .md 파일만 필터 + 프로젝트별 그룹핑
function groupByProject(files) {
  const groups = {};
  for (const file of files) {
    const match = file.match(/^4-프로젝트\/([^/]+)\/.+\.md$/);
    if (!match) continue;
    const project = match[1];
    if (!groups[project]) groups[project] = [];
    // 프로젝트 경로 이후 상대 경로만 저장
    const relativePath = file.replace(`4-프로젝트/${project}/`, "");
    groups[project].push(relativePath);
  }
  return groups;
}

async function main() {
  const files = CHANGED_FILES.split("\n").filter(Boolean);
  const groups = groupByProject(files);
  const projectNames = Object.keys(groups);

  if (projectNames.length === 0) {
    console.log("프로젝트 문서 변경 없음. 알림 건너뜀.");
    return;
  }

  // 스레드 매핑 읽기
  let threads = {};
  try {
    threads = JSON.parse(readFileSync(THREADS_FILE, "utf-8"));
  } catch {
    threads = {};
  }

  let threadsChanged = false;

  for (const project of projectNames) {
    const changedFiles = groups[project];
    const fileList = changedFiles.map((f) => `• ${f}`).join("\n");

    const commitLine = COMMIT_URL
      ? `<${COMMIT_URL}|${COMMIT_MESSAGE}>`
      : COMMIT_MESSAGE;

    if (threads[project]) {
      // 기존 스레드에 reply
      const text = `📝 문서 변경 (${new Date().toISOString().slice(0, 10)})\n\n${fileList}\n\n커밋: ${commitLine}`;
      await slackPost({
        channel: CHANNEL_ID,
        thread_ts: threads[project],
        text,
      });
      console.log(`[${project}] 스레드에 reply 완료`);
    } else {
      // 새 스레드 생성
      const text = `🚀 ${project}`;
      const result = await slackPost({
        channel: CHANNEL_ID,
        text,
      });
      threads[project] = result.ts;
      threadsChanged = true;

      // 첫 reply로 변경 내용 전송
      const replyText = `📝 문서 변경 (${new Date().toISOString().slice(0, 10)})\n\n${fileList}\n\n커밋: ${commitLine}`;
      await slackPost({
        channel: CHANNEL_ID,
        thread_ts: result.ts,
        text: replyText,
      });
      console.log(`[${project}] 새 스레드 생성 + reply 완료`);
    }
  }

  // 매핑 변경 시 저장
  if (threadsChanged) {
    writeFileSync(THREADS_FILE, JSON.stringify(threads, null, 2) + "\n");
    console.log("slack-threads.json 업데이트됨");
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
