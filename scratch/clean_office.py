from pathlib import Path

file_path = Path("web/src/components/office/AutonomousOfficeScreen.tsx")
text = file_path.read_text(encoding="utf-8")

# 1. Remove AgentProfile import
text = text.replace("import type { AgentProfile } from '../../types/zezo'\n", "")

# 2. Remove isSimulating and simulation functions
idx_sim_start = text.find("  const [isSimulating, setIsSimulating] = useState(false)")
idx_sim_end = text.find("  return (\n    <div className=\"flex flex-col w-full h-full min-w-0 min-h-0")

if idx_sim_start != -1 and idx_sim_end != -1:
    clean_sim_block = """  const [simulationToast, setSimulationToast] = useState<string | null>(null)
  const [collabBeam, setCollabBeam] = useState<{
    from: { x: number; y: number }
    to: { x: number; y: number }
    label?: string
  } | null>(null)

  // Helper to show brief toast
  const triggerToast = (msg: string) => {
    setSimulationToast(msg)
    setTimeout(() => setSimulationToast(null), 3000)
  }

"""
    text = text[:idx_sim_start] + clean_sim_block + text[idx_sim_end:]
    print("Removed unused simulation block")

file_path.write_text(text, encoding="utf-8")
print("Cleaned AutonomousOfficeScreen.tsx successfully!")

