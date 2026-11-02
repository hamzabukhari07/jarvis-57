import { forwardRef } from 'react'
import { HugeiconsIcon, type HugeiconsIconProps } from '@hugeicons/react'
import {
  Activity01Icon,
  Add01Icon,
  Alert02Icon,
  AlertCircleIcon,
  ArrowDown01Icon,
  ArrowLeft01Icon,
  ArrowRight01Icon,
  ArrowUp01Icon,
  Atom01Icon,
  AudioWave01Icon,
  BellIcon,
  BookOpen01Icon,
  BotIcon,
  BoxesIcon,
  BrainIcon,
  BrainCircuitIcon,
  Cancel01Icon,
  CancelCircleIcon,
  CheckmarkCircle01Icon,
  CheckmarkCircle02Icon,
  CircleIcon,
  ClipboardIcon,
  Clock01Icon,
  CodeIcon,
  CodeSimpleIcon,
  Compass01Icon,
  ComputerIcon,
  ComputerTerminal01Icon,
  Copy01Icon,
  CpuIcon,
  Database01Icon,
  Delete02Icon,
  Download01Icon,
  EyeIcon,
  EyeOffIcon,
  ExternalLinkIcon,
  FileCodeIcon,
  File01Icon,
  FloppyDiskIcon,
  Folder01Icon,
  FolderGitIcon,
  FolderOpenIcon,
  FolderTreeIcon,
  GitBranchIcon,
  GlobeIcon,
  GridIcon,
  Home01Icon,
  InformationCircleIcon,
  KanbanIcon,
  Key01Icon,
  KeyboardIcon,
  Layers01Icon,
  Layout01Icon,
  Loading01Icon,
  MapPinIcon,
  Maximize01Icon,
  Menu01Icon,
  Message01Icon,
  Mic01Icon,
  MicOffIcon,
  Minimize01Icon,
  Moon01Icon,
  MoreHorizontalIcon,
  Mouse01Icon,
  PaletteIcon,
  PaperclipIcon,
  PanelLeftCloseIcon,
  PanelLeftOpenIcon,
  PauseIcon,
  PencilEdit01Icon,
  PencilIcon,
  PlaneIcon,
  PlayIcon,
  PowerIcon,
  QrCodeIcon,
  RadioIcon,
  RefreshIcon,
  Rocket01Icon,
  Rotate01Icon,
  Search01Icon,
  SentIcon,
  Settings01Icon,
  Shield01Icon,
  ShieldCheckIcon,
  SlidersHorizontalIcon,
  SparklesIcon,
  SquareIcon,
  StopCircleIcon,
  Sun01Icon,
  SunCloud01Icon,
  Tag01Icon,
  CheckIcon,
  UserGroupIcon,
  UserIcon,
  Video01Icon,
  VolumeHighIcon,
  VolumeOffIcon,
  Wifi01Icon,
  WorkflowIcon,
  Wrench01Icon,
  ZapIcon,
  ZoomInIcon,
  ZoomOutIcon,
} from '@hugeicons/core-free-icons'
import type { IconSvgElement } from '@hugeicons/react'

type IconProps = Omit<HugeiconsIconProps, 'icon'>

function createIcon(icon: IconSvgElement, name: string) {
  const Component = forwardRef<SVGSVGElement, IconProps>((props, ref) => (
    <HugeiconsIcon ref={ref} icon={icon} {...props} />
  ))
  Component.displayName = name
  return Component
}

// Keep the existing component names at call sites while rendering only free Hugeicons.
export const Activity = createIcon(Activity01Icon, 'Activity')
export const AlertCircle = createIcon(AlertCircleIcon, 'AlertCircle')
export const AlertTriangle = createIcon(Alert02Icon, 'AlertTriangle')
export const ArrowLeft = createIcon(ArrowLeft01Icon, 'ArrowLeft')
export const ArrowUp = createIcon(ArrowUp01Icon, 'ArrowUp')
export const Atom = createIcon(Atom01Icon, 'Atom')
export const AudioWaveform = createIcon(AudioWave01Icon, 'AudioWaveform')
export const Bell = createIcon(BellIcon, 'Bell')
export const BookOpen = createIcon(BookOpen01Icon, 'BookOpen')
export const Bot = createIcon(BotIcon, 'Bot')
export const Boxes = createIcon(BoxesIcon, 'Boxes')
export const Brain = createIcon(BrainIcon, 'Brain')
export const BrainCircuit = createIcon(BrainCircuitIcon, 'BrainCircuit')
export const Check = createIcon(CheckIcon, 'Check')
export const CheckCircle = createIcon(CheckmarkCircle01Icon, 'CheckCircle')
export const CheckCircle2 = createIcon(CheckmarkCircle02Icon, 'CheckCircle2')
export const ChevronDown = createIcon(ArrowDown01Icon, 'ChevronDown')
export const ChevronLeft = createIcon(ArrowLeft01Icon, 'ChevronLeft')
export const ChevronRight = createIcon(ArrowRight01Icon, 'ChevronRight')
export const ChevronUp = createIcon(ArrowUp01Icon, 'ChevronUp')
export const Circle = createIcon(CircleIcon, 'Circle')
export const Clipboard = createIcon(ClipboardIcon, 'Clipboard')
export const Clock = createIcon(Clock01Icon, 'Clock')
export const CloudSun = createIcon(SunCloud01Icon, 'CloudSun')
export const Code = createIcon(CodeIcon, 'Code')
export const Code2 = createIcon(CodeSimpleIcon, 'Code2')
export const Compass = createIcon(Compass01Icon, 'Compass')
export const Copy = createIcon(Copy01Icon, 'Copy')
export const Cpu = createIcon(CpuIcon, 'Cpu')
export const Database = createIcon(Database01Icon, 'Database')
export const Download = createIcon(Download01Icon, 'Download')
export const Edit3 = createIcon(PencilEdit01Icon, 'Edit3')
export const Ellipsis = createIcon(MoreHorizontalIcon, 'Ellipsis')
export const ExternalLink = createIcon(ExternalLinkIcon, 'ExternalLink')
export const Eye = createIcon(EyeIcon, 'Eye')
export const EyeOff = createIcon(EyeOffIcon, 'EyeOff')
export const FileCode = createIcon(FileCodeIcon, 'FileCode')
export const FileText = createIcon(File01Icon, 'FileText')
export const Folder = createIcon(Folder01Icon, 'Folder')
export const FolderGit2 = createIcon(FolderGitIcon, 'FolderGit2')
export const FolderOpen = createIcon(FolderOpenIcon, 'FolderOpen')
export const FolderTree = createIcon(FolderTreeIcon, 'FolderTree')
export const GitBranch = createIcon(GitBranchIcon, 'GitBranch')
export const Globe = createIcon(GlobeIcon, 'Globe')
export const Home = createIcon(Home01Icon, 'Home')
export const Info = createIcon(InformationCircleIcon, 'Info')
export const Kanban = createIcon(KanbanIcon, 'Kanban')
export const Key = createIcon(Key01Icon, 'Key')
export const KeyRound = createIcon(Key01Icon, 'KeyRound')
export const Keyboard = createIcon(KeyboardIcon, 'Keyboard')
export const Layers = createIcon(Layers01Icon, 'Layers')
export const Layout = createIcon(Layout01Icon, 'Layout')
export const LayoutGrid = createIcon(GridIcon, 'LayoutGrid')
export const Loader2 = createIcon(Loading01Icon, 'Loader2')
export const MapPin = createIcon(MapPinIcon, 'MapPin')
export const Maximize2 = createIcon(Maximize01Icon, 'Maximize2')
export const Menu = createIcon(Menu01Icon, 'Menu')
export const MessageSquare = createIcon(Message01Icon, 'MessageSquare')
export const Mic = createIcon(Mic01Icon, 'Mic')
export const MicOff = createIcon(MicOffIcon, 'MicOff')
export const Minimize2 = createIcon(Minimize01Icon, 'Minimize2')
export const Monitor = createIcon(ComputerIcon, 'Monitor')
export const Moon = createIcon(Moon01Icon, 'Moon')
export const MousePointer = createIcon(Mouse01Icon, 'MousePointer')
export const Palette = createIcon(PaletteIcon, 'Palette')
export const PanelLeftClose = createIcon(PanelLeftCloseIcon, 'PanelLeftClose')
export const PanelLeftOpen = createIcon(PanelLeftOpenIcon, 'PanelLeftOpen')
export const Paperclip = createIcon(PaperclipIcon, 'Paperclip')
export const Pause = createIcon(PauseIcon, 'Pause')
export const Pencil = createIcon(PencilIcon, 'Pencil')
export const Plane = createIcon(PlaneIcon, 'Plane')
export const Play = createIcon(PlayIcon, 'Play')
export const Plus = createIcon(Add01Icon, 'Plus')
export const Power = createIcon(PowerIcon, 'Power')
export const QrCode = createIcon(QrCodeIcon, 'QrCode')
export const Radio = createIcon(RadioIcon, 'Radio')
export const RefreshCw = createIcon(RefreshIcon, 'RefreshCw')
export const Rocket = createIcon(Rocket01Icon, 'Rocket')
export const RotateCcw = createIcon(Rotate01Icon, 'RotateCcw')
export const Save = createIcon(FloppyDiskIcon, 'Save')
export const Search = createIcon(Search01Icon, 'Search')
export const Send = createIcon(SentIcon, 'Send')
export const Settings = createIcon(Settings01Icon, 'Settings')
export const Shield = createIcon(Shield01Icon, 'Shield')
export const ShieldCheck = createIcon(ShieldCheckIcon, 'ShieldCheck')
export const Sliders = createIcon(SlidersHorizontalIcon, 'Sliders')
export const SlidersHorizontal = createIcon(SlidersHorizontalIcon, 'SlidersHorizontal')
export const Sparkles = createIcon(SparklesIcon, 'Sparkles')
export const Square = createIcon(SquareIcon, 'Square')
export const StopCircle = createIcon(StopCircleIcon, 'StopCircle')
export const Sun = createIcon(Sun01Icon, 'Sun')
export const Tag = createIcon(Tag01Icon, 'Tag')
export const Terminal = createIcon(ComputerTerminal01Icon, 'Terminal')
export const Trash2 = createIcon(Delete02Icon, 'Trash2')
export const User = createIcon(UserIcon, 'User')
export const Users = createIcon(UserGroupIcon, 'Users')
export const Video = createIcon(Video01Icon, 'Video')
export const Volume2 = createIcon(VolumeHighIcon, 'Volume2')
export const VolumeX = createIcon(VolumeOffIcon, 'VolumeX')
export const Wifi = createIcon(Wifi01Icon, 'Wifi')
export const Workflow = createIcon(WorkflowIcon, 'Workflow')
export const Wrench = createIcon(Wrench01Icon, 'Wrench')
export const X = createIcon(Cancel01Icon, 'X')
export const XCircle = createIcon(CancelCircleIcon, 'XCircle')
export const Zap = createIcon(ZapIcon, 'Zap')
export const ZoomIn = createIcon(ZoomInIcon, 'ZoomIn')
export const ZoomOut = createIcon(ZoomOutIcon, 'ZoomOut')

