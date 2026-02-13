# 2026-02-golden-set-summarize (Archived)

Status: archived test fixture from the OpenVINO/ONNX evaluation era.

1) input:
   "We met today to review the onboarding plan. The team agreed to move the deadline to next Friday and requested a short checklist by Wednesday. Chris will draft the checklist and send it for review."
   expected:
   "The team moved the onboarding deadline to next Friday; Chris will send a checklist by Wednesday."

2) input:
   "The customer reported intermittent login failures on iOS. Logs show token refresh requests timing out around 8 a.m. We suspect a network proxy issue and plan to add retries. A patch is scheduled for Thursday."
   expected:
   "iOS login failures appear tied to token refresh timeouts; retries and a Thursday patch are planned."

3) input:
   "We need to reorder office supplies: printer paper, pens, sticky notes, and cables. Please place the order today and confirm delivery by Monday."
   expected:
   "Order printer paper, pens, sticky notes, and cables today and confirm delivery by Monday."

4) input:
   "After testing the new model, latency improved by 15%, but accuracy dropped on long inputs. We will keep the old model for emails and use the new one for short messages until we retrain."
   expected:
   "Latency improved 15% but long-input accuracy dropped; keep the old model for emails and use the new one for short messages."

5) input:
   "I will be out of office on Friday and Monday. For urgent requests, contact Sam. I will respond to non-urgent items on Tuesday."
   expected:
   "Out Friday and Monday; urgent requests go to Sam, non-urgent replies Tuesday."

6) input:
   "The customer reported intermittent login failures on iOS during morning hours. Logs show token refresh requests timing out around 8 a.m. We suspect a network proxy issue and plan to add retries. A patch is scheduled for Thursday. In the meantime, support suggested clearing cached tokens and re-authenticating. The issue appears more frequent on older iPhones running iOS 16. We will monitor the error rate daily and send an update by end of week. The team will coordinate with the networking group to confirm proxy health.  The customer reported intermittent login failures on iOS during morning hours. Logs show token refresh requests timing out around 8 a.m. We suspect a network proxy issue and plan to add retries. A patch is scheduled for Thursday. In the meantime, support suggested clearing cached tokens and re-authenticating. The issue appears more frequent on older iPhones running iOS 16. We will monitor the error rate daily and send an update by end of week. The team will coordinate with the networking group to confirm proxy health.  The customer reported intermittent login failures on iOS during morning hours. Logs show token refresh requests timing out around 8 a.m. We suspect a network proxy issue and plan to add retries. A patch is scheduled for Thursday. In the meantime, support suggested clearing cached tokens and re-authenticating. The issue appears more frequent on older iPhones running iOS 16. We will monitor the error rate daily and send an update by end of week. Th"
   expected:
   "iOS login failures seem tied to morning token refresh timeouts; retries, Thursday patch, and monitoring are planned."
