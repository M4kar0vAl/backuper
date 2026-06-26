# Backuper

App for backing up files from one directory to another.

## Scenarios

### File exists in `source` but not in `dest`

This scenario means that new file was added to the `source` directory, and it now should be copied to `dest` and keep the same file name.

**Initial state:**
```text
- src
  - file.txt

- dest
```

**After performing backup:**
```text
- src
  - file.txt

- dest
  - file.txt
```

### File in `source` is newer that the one in `dest`

This scenario means that the file in the `source` directory has been updated since last backup, and it now should be copied to `dest` and overwrite the old file.

**Initial state:**
```text
- src
  - file.txt (26.06.2026)

- dest
  - file.txt (25.06.2026)
```

**After performing backup:**
```text
- src
  - file.txt (26.06.2026)

- dest
  - file.txt (26.06.2026)
```

### File in `source` is older than the one in `dest`

This scenario means that the file in the `source` directory is outdated, and it should NOT be copied to `dest`.

This can happen if someone manually alters the file in `dest`, which leads to conflicts and can potentially cause data loss. If the file in `source` is updated after altering the one in `dest`, then backup process will overwrite file in `dest` even if it contains unique data compared to the one in `source`.

**Initial state:**
```text
- src
  - file.txt (25.06.2026)

- dest
  - file.txt (26.06.2026)
```

**After performing backup:**
```text
- src
  - file.txt (25.06.2026)

- dest
  - file.txt (26.06.2026)
```

Note that nothing changes in this scenario to avoid data loss.

### File exists in `dest` but not in `source`

This scenario means that `dest` has more files than `source` directory. Those files will be left intact because `source` does not have corresponding files to overwrite them.

**Initial state:**
```text
- src

- dest
  - file.txt
```

**After performing backup:**
```text
- src

- dest
  - file.txt
```

## Run

```shell
uv run backuper.py <source> <dest>
```

## Options

- `-s`, `--show-copied` - print copied files after performing backup
