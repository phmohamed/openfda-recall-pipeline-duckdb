import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
m = pd.read_csv("data/monthly_by_class.csv", parse_dates=["month"]).pivot(index="month", columns="classification", values="recalls").fillna(0)
r = pd.read_csv("data/reason_groups.csv")
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw={"width_ratios": [1.5, 1]})
m.plot.bar(stacked=True, ax=ax[0], color=["#b2182b", "#f4a582", "#92c5de"], width=.85)
ax[0].set_xticklabels([d.strftime("%Y-%m") if i % 3 == 0 else "" for i, d in enumerate(m.index)], rotation=45, ha="right")
ax[0].set_xlabel(""); ax[0].set_ylabel("Product recall records"); ax[0].set_title("Drug recalls by report month and class")
ax[1].barh(r.reason_group[::-1], r.recalls[::-1], color="#4d4d4d"); ax[1].set_title("Recalls by reason group (keyword rules)")
plt.tight_layout(); plt.savefig("figures/recalls_overview.png", dpi=100)
