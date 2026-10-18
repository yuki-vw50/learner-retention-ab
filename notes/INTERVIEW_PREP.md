# Interview Prep: Learner Retention & A/B Testing Project

Read this, run the code yourself, and change at least one thing before you put the project on
your resume. Interviewers will ask "why did you do X?", and you should be able to answer from memory.

## 30-second summary
"I analyzed what keeps learners coming back to a learning app. With about 13 million Duolingo practice
records, I used SQL to build cohort retention curves and a forgetting curve showing how recall drops when
words aren't reviewed. Then I analyzed a real A/B test with 90,000 players. Moving a progress gate later
cut Day-7 retention by 0.8 points, which was significant, so I recommended keeping it. I also caught a
sample ratio mismatch in the experiment, which I flagged as a caveat."

## Questions you should be ready for

**What is a two-proportion z-test, and why use it?**
Retention is yes/no per player, so each group has a proportion. The z-test checks whether the two
proportions differ by more than random chance would explain. With 45K players per group, the normal
approximation works well.

**What does p = 0.0016 mean?**
If the gate change truly had no effect, a difference this large would show up only about 0.16% of
the time by chance. It does *not* mean "99.84% chance the treatment is worse".

**Why also do a bootstrap?**
It's a check that doesn't depend on the z-test's assumptions. I resampled each group 2,000 times and
recomputed the difference each time. Control won in 99.9% of resamples, which agrees with the z-test.

**What is SRM, and why does it matter?**
Sample ratio mismatch: the experiment was meant to split traffic 50/50, but treatment got 50.44%. A
chi-square test says that's unlikely by chance (p = 0.009). It usually means a bug, such as some users
not being logged in one group. If the missing users differ systematically, the results can be biased.
That's why I flagged it instead of just reporting the p-value.

**Why is Day-1 "not significant" not the same as "no effect"?**
Power. With this sample size, the test can only reliably detect a Day-1 change of about 0.9 points.
The observed change was 0.59 points, which is smaller than the test can detect, so the result is
inconclusive.

**Why are the engagement-band results "descriptive only"?**
Rounds played happens after users are assigned to a group, and the treatment itself can change how
many rounds people play. Splitting by it mixes the treatment effect with who chose to keep playing
(post-treatment bias).

**How did you define retention?**
Day-N retention = share of a cohort active on exactly day N after first appearing. I only kept cohorts
with a full 7 days of follow-up, so later cohorts don't look worse just because the data ends.

**What's the biggest limitation?**
The Duolingo data is a two-week research sample from 2013. "First appeared" isn't necessarily sign-up
day, so it measures returning activity, not true new-user retention.

**What would you do next?**
- Test spaced-repetition reminders: send a nudge when a word's predicted recall drops below a threshold.
- Predict which learners are likely to churn using their first 3 days of activity.
- Re-run the A/B test after engineering resolves the SRM.

## Know your SQL
Be able to explain each of these without looking:
- **CTE (`WITH ... AS`)**: breaks a query into named steps (see `03_cohort_retention.sql`).
- **Window functions**: `ROW_NUMBER() OVER (PARTITION BY language ORDER BY recall)` ranks words
  within each language; `NTILE(4)` splits learners into quartiles; `AVG(...) OVER (ROWS 6 PRECEDING)`
  gives a rolling average.
- **Conditional aggregation**: `MAX(CASE WHEN day_n = 7 THEN 1 ELSE 0 END)` flags users active on day 7.
