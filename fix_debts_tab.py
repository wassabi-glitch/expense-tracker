import re
import os

log_path = r'C:\Users\me\.gemini\antigravity-ide\brain\54d3f5da-9cbf-4859-9b94-5f09ba4469bd\.system_generated\tasks\task-17.log'
with open(log_path, 'r', encoding='utf-8') as f:
    log_content = f.read()

diff_match = re.search(r'(diff --git a/frontend/src/features/obligations/components/DebtsTab\.jsx b/frontend/src/features/obligations/components/DebtsTab\.jsx.*?)(?=diff --git|$)', log_content, re.DOTALL)
if diff_match:
    diff = diff_match.group(1)
    
    with open('full_debts_tab.patch', 'w', encoding='utf-8') as f:
        f.write(diff)
        
    os.system('git checkout frontend/src/features/obligations/components/DebtsTab.jsx')
    res = os.system('git apply full_debts_tab.patch')
    print('Applied full patch. Res:', res)
    
    # Now fix the missing DebtRow
    with open('frontend/src/features/obligations/components/DebtsTab.jsx', 'r', encoding='utf-8') as f:
        content = f.read()
        
    target = """      </DialogContent>
    </Dialog>
    <Card className="rounded-lg border-border py-0 shadow-none">
      <CardContent className="p-4">"""

    replacement = """      </DialogContent>
    </Dialog>
  );
}

function DebtRow({ debt, onOpen, onDelete, onPayoff }) {
  const Icon = kindIcon(debt);
  const total = Number(debt.initial_amount || 0) + Number(debt.total_charges || 0);
  const paid = debt.total_paid || 0;
  const progress = total > 0 ? Math.min(100, Math.round((paid / total) * 100)) : 0;
  const isOwing = debt.debt_type === "OWING";
  const isWalletObligation = debt.source_type === "WALLET";
  const RowIcon = isWalletObligation ? WalletCards : Icon;

  return (
    <Card className="rounded-lg border-border py-0 shadow-none">
      <CardContent className="p-4">"""

    if target in content:
        content = content.replace(target, replacement)
        with open('frontend/src/features/obligations/components/DebtsTab.jsx', 'w', encoding='utf-8') as f:
            f.write(content)
        print('Fixed DebtRow and applied Issue 3 change.')
    else:
        print('Could not find target to fix DebtRow!')
else:
    print('Diff not found.')
