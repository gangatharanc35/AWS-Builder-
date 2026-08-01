

\# 🧠 SmartDigest AI — Weekly Information Noise Killer



> \*\*Turn your chaotic weekly newsletters, RSS feeds, and updates into ONE clean, AI-prioritized digest.\*\*





\## 🎯 The Problem



Every week, knowledge workers waste \*\*30-60 minutes\*\* scanning through dozens of newsletters, RSS feeds, and notification emails trying to find what actually matters. Information overload is real, and it's stealing your productive hours.



\## 💡 The Solution



\*\*SmartDigest AI\*\* automatically:

1\. \*\*Collects\*\* content from your configured RSS feeds and newsletter sources

2\. \*\*Analyzes\*\* each item using Amazon Bedrock (Nova model) for relevance and importance

3\. \*\*Categorizes\*\* content into priority tiers (🔴 Must Read, 🟡 Worth Knowing, 🟢 Optional)

4\. \*\*Summarizes\*\* each article into 2-3 sentence key takeaways

5\. \*\*Delivers\*\* a single, clean weekly digest via email or web dashboard



\## 🏗️ Architecture
┌─────────────────┐ ┌──────────────────┐ ┌─────────────────┐ │ EventBridge │────▶│ Feed Collector │────▶│ DynamoDB │ │ (Weekly Cron) │ │ (Lambda) │ │ (Raw Items) │ └─────────────────┘ └──────────────────┘ └────────┬────────┘ │ ▼ ┌─────────────────┐ ┌──────────────────┐ ┌─────────────────┐ │ S3 Static Site │◀────│ Digest Delivery │◀────│ AI Summarizer │ │ (Frontend) │ │ (Lambda + SES) │ │ (Lambda+Bedrock)│ └─────────────────┘ └──────────────────┘ └─────────────────┘



