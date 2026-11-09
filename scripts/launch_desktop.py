import sys

if len(sys.argv) >= 4 and sys.argv[1] == "--fighter-contract":
    from defjam_caf.fighter_mod import run_contract
    raise SystemExit(run_contract(sys.argv[2], sys.argv[3], sys.argv[4:]))

from defjam_caf.desktop import main

raise SystemExit(main())
