import subprocess
import codecs

result = subprocess.run(['python', '-m', 'pytest', 'tests/', '-v', '--tb=short'], capture_output=True, text=True)

with codecs.open('pytest_output.txt', 'w', 'utf-8') as f:
    f.write(result.stdout)
    if result.stderr:
        f.write("\n\nSTDERR:\n")
        f.write(result.stderr)
