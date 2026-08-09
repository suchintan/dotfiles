# RULES.md

## Final-message contract

The user often sees only the final message of a turn. Interim narration and analysis are not reliably shown.

- Make the final message self-contained.
- Restate every conclusion, number, command, path, or table the user needs to act.
- Never refer to earlier assistant messages. Do not write "as shown above" or "see my previous message".
- If a long artifact matters, write it to a file and give the path.

<!-- Note: a user-level RULES.md shadows any project .omp/RULES.md (omp does not
     concatenate them). If a project ever needs its own sticky rules, fold these
     bullets into that project file too. -->
