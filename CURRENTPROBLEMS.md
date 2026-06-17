1. Cant add charges to a debt that has been marked as paid
2. Debt staying as Paid even tho I delete charges associated to that debt in expenses page.
3. Income source is not getting updated in Edit Debt form and income entries table
4. There could be potential links with expense refund and debt charges. When I refund an expense, it should be deducted from the debt.
5. We could create a separate category for debt charges.
6. There could be links with Debt type "I owe"  money_transfered: false and recurring expenses. For example, my car mechanic charges me 50k and i tell him i will pay him next week. It happens next week, so i can create a recurring expense template with frequence "One time" and category "Debt charges" and it should be deducted from the debt, and shown in expenses page as well.
7. My system does not know to which income source the debt charges. For example, when I lent 500k to my cousin for his business and tell him to pay me extra 100k, my system should know to which income source the extra 100k belongs in my income entries table. As of now, it shows it as a No source.
8. We should give our user a guidance on wheter or not they should specify income source or expense category when creating a debt. I would like to know what are the best practices for this. So that our user can make an informed decision.
9. Imagine a scenario where a user lents 300k to his friend and adds 100k charge on top of the debt. User gets 400k back after 2 months, and our system records the 100k charge as an income. However, now , if user goes back to his debt , the Debt is already marked as Paid, so user cant add any more charges to it. Also, if he goes back to his income page and deletes the 100k charge he got, our system does not deduct that from the debt and the debt remains as paid. We should create a mechanism to handle this. Interestingly , if user deletes the 100k charge payment from the Debt Payment history list, it is getting deducted from the debt and the debt is getting marked as active again. But should it not be a two-way street? I mean, if user deletes the income entry, it should be deducted from the debt as well.
10. Multi category selection for debts expense
11. Multi Item selection when creating an expense in Basket mode.
12. Remove the category and income source selection for debts with money_transfered:false in Record payment form.
13. We should probably remove update category and income source for debts money_transfered: true from Update form
14. Polish up debt payment history modal
15. I am considering Debt Events architecture. Basically, debt events will be any event that happens with the debt, such as , payment, charge, forgive, archive, etc. And each event will have its own type, amount, date, etc. And we can have a separate table for debt events, and each debt will have a one-to-many relationship with debt events. So, when user creates a debt, it will have a debt event of type "CREATE" and amount of "initial_amount", and when user makes a payment, it will have a debt event of type "PAYMENT" and amount of "payment_amount", and when user adds a charge, it will have a debt event of type "CHARGE" and amount of "charge_amount", and when user forgives the debt, it will have a debt event of type "FORGIVE" and amount of "remaining_amount", and when user archives the debt, it will have a debt event of type "ARCHIVE" and amount of "remaining_amount". And we can have a separate table for debt events, and each debt will have a one-to-many relationship with debt events. So, when user creates a debt, it will have a debt event of type "CREATE" and amount of "initial_amount", and when user makes a payment, it will have a debt event of type "PAYMENT" and amount of "payment_amount", and when user adds a charge, it will have a debt event of type "CHARGE" and amount of "charge_amount", and when user forgives the debt, it will have a debt event of type "FORGIVE" and amount of "remaining_amount", and when user archives the debt, it will have a debt event of type "ARCHIVE" and amount of "remaining_amount". 
16. I am thinking of an update for Forgive debt feature,basically I would like to forgive portion of the debt as well rather than only default remaining amount.
17. I am concerned if nothing bad happens if we allow to update the amount of debt_charge in Expenses page like regular expenses. Let's try to think of scenarios.For example, your friend lends you 500k and he asks 100k for charges.So you pay 600k and the 100k gets recorded as debt_expense ref_type, transaction_type: Expense, and so it is basically treated as an expense.Now, you go to expenses page and update the charge amount from 100k to 1M. I am wondering if our app does not crash because 500k+1M=1500k and basically it it means we are exceeding 600k total Remaining amount by 900k which I think not allowed in our system.I would like you to help me think about this scenario deeply. I want to know if it is a good idea to allow this.
18. The same goes to debt_income ref_type. For example, you lend your friend 500k+100k and 100k goes to your Income,now if you go to income page and update the 100k to 1M, I wonder if our system wont crash because we are exceeding Remaining amount of debt.
19. I think this scenario is worth considereing for any type of debt.
20. Let's think of more cases. Imagine your broke your friend's phone and now you owe him 10M.You pay 5M in 1st month,and that 5M gets recorded as Expense in expenses page.Then, you delete the debt, my question if that 5M recorded as Expense should be deleted as well or not.The same question applies for reverse scanarios,for example, your client owed you 10M, paid 5M, and then the 5M gets recorded as your Income,and then you delete the debt, and should that 5M Income recorded In Income page be  deleted with the debt or not?
21. We should consider adding "details" page/dialog for each debt in the Debts page.
22. We should consider adding "details" page/dialog for each expense in the Expenses page.
23. We should consider adding "details" page/dialog for each income in the Income page.
24. We should consider adding "Add taxes" feature for each income entry.
25. We should consider adding "Sell" action for certain expenses so that it does not create fake income entries.For example, you buy a laptop for 10M, a year later you sell it for 6M, and that 6M should not get recorded as Income. I think this is a quite big feature if we want to get into this rabbit hole.So we should think about it deeply before coding anything yet.
26. We should consider adding "increase item count" feature in Basket mode mentioned above at 11. Basically, instead of adding the same item to the basket multiple times, we can just increase the count of the item in the basket.
27. We should consider pivoting our Expenses to Event-driven architecture as well. I am saying this because I just realized that there are too many connections between expenses and other features and expenses themselves contain many actions.We should think more deeply about this and then decide.
28. We should seperate categories from budgets and make categories to have custom subcategories. I am very confused about this. Can you give me a clear picture of what I am thinking? 


> No — expense categories and budgets should ideally be separate concepts. Categories describe what the expense is, while budgets describe spending limits or plans. Your current merged approach is valid early on, but separating them later will give your system much more flexibility and scalability.

I would like you to explain in simple terms what you think about this concept because I myself cant properly understand it. I want you to be brutally honest.
Yeah basically Budgets will be parents of categories, categories of custom subcategories, and expenses will be children of categories/subcategories.


29. We should consider adding NEUTRAL_FLOW actions for Wallets, such as asset_sale, passthrough, insurance_payout, security_deposit, etc.

30. Considering expense templates that user can precreate only once and then use it whenever he/she wants to create an expense with a click of a button.

31. Once these problems are sorted out, we should start working on new features listed in FEATURES.md.



32. What if there will be some unspent money left on Project budget?
33. Autoallocation when user receives his income.


Yes, project expenses should absolutely be allowed to carry subcategories.
No, I would not rush into project-specific subcategory limit enforcement unless we want the full multi-layer planning complexity and are ready to explain it clearly.



34. no ui for merge