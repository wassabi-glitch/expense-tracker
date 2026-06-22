import re

with open('frontend/src/features/expenses/Expenses.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the whole recordingMode and recurringWallet block with just recurringWallet block
pattern = r'<div className="grid grid-cols-2 gap-4">\s*<div className="space-y-2">\s*<label className="text-xs font-semibold">\{t\("recurring\.recordingMode"\)\}</label>\s*<Select value=\{recurringRecordingMode\} onValueChange=\{setRecurringRecordingMode\}>.*?</Select>\s*</div>\s*<div className="space-y-2">\s*<label className="text-xs font-semibold">\s*\{recurringRecordingMode === "AUTO_RECORD" \? t\("recurring\.automaticWallet"\) : t\("recurring\.preferredWallet"\)\}\s*</label>'

replacement = '<div className="grid grid-cols-1 gap-4">\n              <div className="space-y-2">\n                <label className="text-xs font-semibold">{t("recurring.preferredWallet")}</label>'

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Replace the recurringRecordingMode check for None option in wallet select
content = re.sub(r'\{recurringRecordingMode === "CONFIRM_EACH" && \([\s\S]*?<SelectItem value="none">\{t\("wallets\.none"\)\}</SelectItem>[\s\S]*?\)\}', '<SelectItem value="none">{t("wallets.none")}</SelectItem>', content)

with open('frontend/src/features/expenses/Expenses.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
