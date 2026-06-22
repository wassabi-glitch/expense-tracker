import re

with open('frontend/src/features/expenses/Expenses.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove state
content = re.sub(r'^\s*const \[recurringRecordingMode, setRecurringRecordingMode\] = React\.useState\("CONFIRM_EACH"\);\n', '', content, flags=re.MULTILINE)

# 2. Remove reset
content = re.sub(r'^\s*setRecurringRecordingMode\("CONFIRM_EACH"\);\n', '', content, flags=re.MULTILINE)

# 3. Remove validation
content = re.sub(r'^\s*if \(recurringRecordingMode === "AUTO_RECORD" && !recurringWalletId\) \{[\s\S]*?^\s*\}\n', '', content, flags=re.MULTILINE)

# 4. Remove recording_mode from payload
content = re.sub(r'^\s*recording_mode: recurringRecordingMode,\n', '', content, flags=re.MULTILINE)

# 5. Remove UI section
content = re.sub(r'<div className=\"grid grid-cols-2 gap-4\">\s*<div className=\"space-y-2\">\s*<label className=\"text-xs font-semibold\">\{t\(\"recurring\.recordingMode\"\)\}</label>\s*<Select value=\{recurringRecordingMode\} onValueChange=\{setRecurringRecordingMode\}>.*?</Select>\s*</div>\s*<div className=\"space-y-2\">\s*<label className=\"text-xs font-semibold\">\s*\{recurringRecordingMode === \"AUTO_RECORD\" \? t\(\"recurring\.automaticWallet\"\) : t\(\"recurring\.preferredWallet\"\)\}\s*</label>', '<div className=\"grid grid-cols-1 gap-4\">\n              <div className=\"space-y-2\">\n                <label className=\"text-xs font-semibold\">{t("recurring.preferredWallet")}</label>', content, flags=re.DOTALL)

# 6. Remove the None option logic inside the wallet dropdown for CONFIRM_EACH
content = re.sub(r'\{recurringRecordingMode === \"CONFIRM_EACH\" && \([\s\S]*?<SelectItem value=\"none\">\{t\(\"wallets\.none\"\)\}</SelectItem>[\s\S]*?\)\}', '<SelectItem value=\"none\">{t(\"wallets.none\")}</SelectItem>', content)

with open('frontend/src/features/expenses/Expenses.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
