import sys, os
sys.path.insert(0, r'C:\Users\emanu\Desktop\MCM ENGINE\MCM_ENGINE_FLASK')

try:
    from app.reports.pdf_utils import LOGO_PATH
    print('LOGO_PATH:', LOGO_PATH)
    print('Logo found:', os.path.isfile(LOGO_PATH))
except Exception as e:
    print('ERROR importing pdf_utils:', e)
    sys.exit(1)

try:
    from app.reports.report_comportamento import genera_report
    print('Generating PDF...')
    buf = genera_report([])
    size = len(buf.getvalue())
    print(f'PDF OK: {size:,} bytes')

    out = r'C:\Users\emanu\Desktop\MCM ENGINE\MCM_ENGINE_FLASK\test_logo_output.pdf'
    buf.seek(0)
    with open(out, 'wb') as f:
        f.write(buf.read())
    print('Saved:', out)
except Exception as e:
    import traceback
    print('ERROR generating PDF:')
    traceback.print_exc()
    sys.exit(1)
