# Wordlists — Mastery Skill & Usage Guide

> **Purpose of this file:** teach any agent (or human) how to *understand and select*
> the right wordlist instantly, without manually listing/filtering directories every time.
> Read the **Decision Guide (§6)** and **Go-To Table (§7)** first; use the rest for reference.
>
> A machine-readable inventory of every file (path, bytes, line count) lives next to this
> file at [`index.json`](index.json). Use `jq`/`grep` on it for fast programmatic lookup.

---

## 1. Big picture

Total footprint ≈ **1.9 GB**, ~6,500 files, under `/home/kou/Documents/mcparrot/wordlists/`.

| Category | Files | Size | What it's for |
|---|---|---|---|
| `Ai/` | 13 | 5 MB | LLM red-teaming: jailbreak/bias/leakage/recall prompts |
| `Discovery/` | 435 | 485 MB | Subdomain + web content/directory discovery |
| `Fuzzing/` | 4657 | 365 MB | Input/parameter fuzzing payloads (XSS, LFI, XXE, SSTI, UA, digits) |
| `Miscellaneous/` | 272 | 247 MB | Natural-language wordlists, domains, security-question answers |
| `Passwords/` | 723 | 631 MB | Password + default-credential lists for brute force/spraying |
| `Pattern-Matching/` | 11 | 53 KB | Grep patterns for source/fs auditing (magic hashes, errors) |
| `Payloads/` | 37 | 55 MB | Malformed/binary payloads: zip bombs, traversal, EICAR, images |
| `Usernames/` | 18 | 87 MB | Username lists for credential guessing |
| `Web-Shells/` | 61 | 232 KB | Post-exploitation shells (laudanum, FuzzDB, CMS-specific) |

---

## 2. Where things live (taxonomy)

### `Discovery/`
- **`DNS/`** — subdomain brute-force lists. Biggest: `FUZZSUBS_CYFARE_{1,2}.txt` (73 MB each),
  `n0kovo_subdomains.txt` (49 MB), `dns-Jhaddix.txt` (25 MB, ~2.17M lines),
  `bug-bounty-program-subdomains-trickest-inventory.txt` (24 MB). Ranked/quick:
  `subdomains-top1million-{5000,20000,110000}.txt`, `bitquark-subdomains-top100000.txt`,
  `namelist.txt`, `fierce-hostlist.txt`, `shubs-subdomains.txt`. (`subdomains-top1million-full.7z` needs extraction.)
- **`Web-Content/`** — directory/file brute-force. Classic DirBuster + raft sets (see §3).
  `common.txt`, `quickhits.txt`, `big.txt`, `combined_directories.txt`, `combined_words.txt`.
  Also CMS-specific (`CMS/trickest-cms-wordlist/*`), `api/`, `Service-Specific/`,
  `Programming-Language-Specific/`, `Web-Servers/`, `File-Extensions-Universal-SVNDigger-Project/`.
- Small helpers: `File-System/`, `Infrastructure/`, `Mainframe/`, `SNMP/`, `Variables/`.

### `Fuzzing/` (root = the good stuff)
- Classic fuzz payloads live directly in `Fuzzing/`: `big-list-of-naughty-strings.txt`,
  `command-injection-commix.txt`, `XXE-Fuzzing.txt`, `XML-FUZZ.txt`, `JSON.Fuzzing.txt`,
  `FormatString-Jhaddix.txt`, `HTML5sec-Injections-Jhaddix.txt`, `SSI-Injection-Jhaddix.txt`,
  `template-engines-*`, `LDAP*`, `login_bypass.txt`, `Metacharacters.fuzzdb.txt`,
  `UnixAttacks.fuzzdb.txt`, `Windows-Attacks.fuzzdb.txt`, `URI-XSS.fuzzdb.txt`.
- Subdirs: `LFI/` (10 files), `XSS/` (37 files), `Databases/`, `Dates/`, `Amounts/`,
  `0-6-digit` number lists (`3-digits-000-999.txt` … `6-digits-000000-999999.txt`).
- ⚠️ `User-Agents/` is 4499 files / 350 MB — only touch if you specifically need UA fuzzing.

### `Miscellaneous/`
- **`Words/`** — language dictionaries: `Dutch-words.txt` (76 MB), Moby Project
  (`Moby-Words-II/SINGLE.TXT`, `Moby-Language-II/*`), `lang-english.txt` (354K lines),
  `lang-{french,spanish,german,portuguese}.txt`.
- Root: `domains-1million-top.txt`, `top-domains-{alexa,majestic}.csv.zip`,
  `pi-large.txt` (4 MB of pi digits).
- `Security-Question-Answers/` — `dates.txt`, `city-state-country.txt`, etc.
- `Danish-Wordlists-n0kovo/` — Danish names/streets/words.

### `Passwords/`
- **`Common-Credentials/`** — ranked, best-first: `Pwdb_top-10000000.txt` (90 MB),
  `xato-net-10-million-passwords.txt` (46 MB), `Language-Specific/*` (Dutch/German/Chinese/Polish…).
- **`Leaked-Databases/`** — `rockyou.txt.tar.gz` / `rockyou-withcount.txt.tar.gz` (extract first),
  `alleged-gmail-passwords.txt` (29 MB), `md5decryptor-uk.txt` (32 MB).
- **`Default-Credentials/`** — per-service `*-betterdefaultpasslist.txt`
  (ftp, ssh, telnet, mysql, mssql, oracle, postgres, db2, tomcat, vnc, windows, avaya, citrix…),
  `default-passwords.csv`, `scada-pass.csv`, `cirt-net_collection.txt`, and
  `Routers/` (466 vendor router files).
- Other: `Software/bt4-password.txt`, `darkc0de.txt`, `Wikipedia/wikipedia_*_top-1000000.txt`,
  `Keyboard-Walks/`, `WiFi-WPA/`, `PHP-Hashes/`, `Permutations/`, `Honeypot-Captures/`, `Cracked-Hashes/`.

### `Usernames/`
- `xato-net-10-million-usernames.txt` (81 MB; `-dup` variant = 4.9 MB with dups),
  `top-usernames-shortlist.txt` (17 lines — **start here**), `Names/names.txt`,
  `Names/*-top1000.txt`, `cirt-default-usernames.txt`, `sap-default-usernames.txt`,
  `mssql-usernames-*.txt`, `CommonAdminBase64.txt`.

### `Pattern-Matching/`
- `php-magic-hashes.txt` (1545 lines), `errors.txt`, `malicious.txt`, `repo-scan.txt`,
  `grepstrings-*.txt`, `dangerous-functions-angular.txt`, `pcap-strings.txt`.

### `Payloads/`
- `Zip-Bombs/` (`zbxl.zip` 44 MB, `zblg.zip` 9.4 MB), `Zip-Traversal/`,
  `PHPInfo.zip`, `Images/` (`uber.gif`, `lottapixel.jpg`), `Anti-Virus/` (EICAR),
  `Flash/xssproject.swf`, `File-Names/`.

### `Web-Shells/`
- `laudanum-1.0/` (php/asp/aspx/jsp/cfm shells), `FuzzDB/` (`nc.exe`, `cmd.sh`),
  `backdoor_list.txt`, `WordPress/`, `Vtiger/`, `Magento/`.

### `Ai/`
- `LLM_Testing/`: `Ethical_and_Safety_Boundaries/jailbreak_prompts_*.csv` (~24.8k + 7.6k rows),
  `Bias_Testing/`, `Data_Leakage/`, `Memory_Recall_Testing/`, `Divergence_attack/`.

---

## 3. Naming-convention decoder

| Pattern | Meaning | Action |
|---|---|---|
| `raft-{small,medium,large}-{directories,files,words,extensions}[-lowercase]` | SecLists gobuster/ffuf sets | Pick `-directories` for dirs, `-files`/`-words` for files, `-extensions` for ext |
| `DirBuster-2007_directory-list-2.3-{small,medium,big}[-lowercase]` | Classic DirBuster lists | medium = good default |
| `common.txt`, `quickhits.txt`, `big.txt` | Fast "first pass" dir lists | run `quickhits.txt` first |
| `*-top{N}` / `top{N}` / `top1million` | Ranked by real-world frequency | **Always prefer these first** (small & high-yield) |
| `-small` / `-medium` / `-large` / `-big` / `-full` | Coverage/size tier | escalate small → big as needed |
| `-lowercase` | Case-normalized (fewer dupes) | Prefer over non-lowercase |
| `combined_*` | Merged from multiple sources | Good coverage, may contain dupes |
| `*-betterdefaultpasslist.txt` | Per-service default creds | Match to target service |
| `default-passwords.csv` / `scada-pass.csv` | Consolidated default creds | grep by vendor/product |
| `Language-Specific/` | Localized lists | Use when target language known |
| `withcount` | Two columns: `password  count` | strip count col for tools |
| `-dup` | Still contains duplicates | Prefer the non-`-dup` version |
| `.tar.gz` / `.7z` / `.zip` / `.tgz` | Archive | **Extract before use** |
| `.csv` | Comma-separated, may have header | skip header / pick column |
| `.json` | Structured data | parse, don't feed raw to brute tools |

---

## 4. File format & compression notes

- **Default format:** one entry per line (LF), no header.
- **Compressed-but-in-use:** many >100 MB source lists were compressed → extract with
  `tar xzf`, `7z x`, or `unzip` into `playground/` before feeding to tools.
- **Non-text files:** `Payloads/` (zip bombs, images, SWF) and `FuzzDB/nc.exe` are binaries —
  never feed them as wordlists.
- **CSVs with headers:** e.g. `default-passwords.csv`, `scada-pass.csv`, `Ai/*.csv` —
  inspect with `head` first.

---

## 5. Size tiers (performance guardrails)

| Tier | Size | Guidance |
|---|---|---|
| 🟢 Fast | < 1 MB | Use liberally; ideal first pass |
| 🟡 Medium | 1–10 MB | Fine, but parallelize / set timeout |
| 🟠 Large | 10–30 MB | Pre-filter (`head`, `sort -u`, `grep`) or use ranked `-topN` subset |
| 🔴 Huge | > 30 MB | Avoid raw; **always** pre-filter or extract a ranked subset |

Huge lists to watch: `FUZZSUBS_CYFARE_*` (73 MB), `Dutch-words.txt` (76 MB),
`Pwdb_top-10000000.txt` (90 MB), `xato-net-10-million-usernames.txt` (81 MB),
`rockyou.txt.tar.gz` (53 MB), `User-Agents/*` (many >20 MB).

---

## 6. Decision guide (task → wordlist)

| Task | Start with (fast) | Escalate to (thorough) |
|---|---|---|
| Directory brute-force (gobuster/ffuf) | `Discovery/Web-Content/quickhits.txt`, `common.txt` | `raft-medium-directories.txt` → `raft-large-directories.txt` |
| File brute-force | `raft-small-files.txt` | `raft-medium-files.txt` / `raft-large-files.txt` |
| Extension discovery | `web-extensions.txt` | `raft-medium-extensions.txt` / `web-extensions-big.txt` |
| Subdomain enum (DNS) | `subdomains-top1million-5000.txt` | `-20000.txt` → `-110000.txt` → `dns-Jhaddix.txt` |
| Vhost brute-force | `namelist.txt`, `combined_subdomains.txt` | `shubs-subdomains.txt` |
| Password spray/brute (ranked) | `Passwords/Common-Credentials/` small `-top*` | `darkc0de.txt` → `rockyou.txt` (extract) |
| Default creds | `*-betterdefaultpasslist.txt` (match service) | `default-passwords.csv`, `cirt-net_collection.txt` |
| Username guessing | `Usernames/top-usernames-shortlist.txt` | `Names/names.txt` → `xato-net-10-million-usernames.txt` |
| Input fuzzing (XSS/SQLi/LFI/XXE/SSTI) | `Fuzzing/` root named lists | `Fuzzing/XSS/`, `Fuzzing/LFI/` |
| Numeric field brute | `Fuzzing/3-digits-000-999.txt` … `6-digits` | generate ranges |
| Source/fs audit (grep) | `Pattern-Matching/grepstrings-basic.txt` | `php-magic-hashes.txt`, `errors.txt` |
| Upload/DoS test | `Payloads/PHPInfo.zip`, `Zip-Bombs/zbxl.zip` | `Images/uber.gif`, `lottapixel.jpg` |
| Post-exploit shell | `Web-Shells/laudanum-1.0/<lang>/shell.*` | `backdoor_list.txt` |
| LLM red-team | `Ai/LLM_Testing/Ethical_and_Safety_Boundaries/jailbreak_prompts_*.csv` | `Bias_Testing/`, `Divergence_attack/` |

---

## 7. Go-to quick-reference (copy-paste paths)

```
# Directory / file brute-force
Discovery/Web-Content/quickhits.txt
Discovery/Web-Content/common.txt
Discovery/Web-Content/raft-medium-directories-lowercase.txt
Discovery/Web-Content/raft-large-directories-lowercase.txt

# Subdomain / vhost
Discovery/DNS/subdomains-top1million-5000.txt
Discovery/DNS/subdomains-top1million-20000.txt
Discovery/DNS/namelist.txt
Discovery/DNS/dns-Jhaddix.txt

# Extensions
Discovery/Web-Content/web-extensions.txt
Discovery/Web-Content/raft-small-extensions.txt

# Passwords (ranked, best-first)
Passwords/Common-Credentials/Pwdb_top-10000000.txt        # huge — pre-filter
Passwords/darkc0de.txt
Passwords/Leaked-Databases/rockyou.txt.tar.gz             # extract first
Passwords/Default-Credentials/ftp-betterdefaultpasslist.txt
Passwords/Default-Credentials/default-passwords.csv

# Usernames
Usernames/top-usernames-shortlist.txt
Usernames/Names/names.txt
Usernames/xato-net-10-million-usernames.txt               # huge — pre-filter

# Fuzzing
Fuzzing/big-list-of-naughty-strings.txt
Fuzzing/command-injection-commix.txt
Fuzzing/XXE-Fuzzing.txt
Fuzzing/LFI/
Fuzzing/XSS/

# Pattern matching
Pattern-Matching/php-magic-hashes.txt
Pattern-Matching/grepstrings-basic.txt
```

---

## 8. Tips to avoid manual filtering

1. **Prefer ranked `-topN` lists** — they give most of the value at a fraction of the size.
2. **Use `head -n N`** on huge lists to build a quick subset; `sort -u` to dedupe.
3. **Prefer `-lowercase`** variants — they cut duplicate case permutations.
4. **Match language/vendor** — use `Language-Specific`, `Routers/`, and `*-betterdefaultpasslist` for targeted attacks.
5. **Extract archives into `playground/`** (never feed `.tar.gz`/`.7z` directly).
6. **Query `index.json`** for exact paths/sizes/line counts instead of `ls`-ing around:
   ```bash
   jq -r '.Passwords.entries[] | select(.path|test("rockyou"))' wordlists/index.json
   ```
7. **Skip `User-Agents/`** unless the task is explicitly UA fuzzing (it's 350 MB of noise otherwise).
