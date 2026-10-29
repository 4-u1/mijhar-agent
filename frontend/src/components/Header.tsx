import React from 'react';
import { Shield, Sparkles, Globe, Terminal, FileText, CheckCircle2, AlertTriangle, Layers, Cpu } from 'lucide-react';
import { Language } from '../types/audit';

interface HeaderProps {
  currentTab: string;
  onTabChange: (tab: string) => void;
  language: Language;
  onToggleLanguage: () => void;
  pendingHITLCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onTabChange,
  language,
  onToggleLanguage,
  pendingHITLCount,
}) => {
  const isAr = language === 'ar';

  const navItems = [
    { id: 'dashboard', labelAr: 'لوحة التحكم', labelEn: 'Dashboard', icon: Layers },
    { id: 'upload', labelAr: 'تدقيق مستند', labelEn: 'Audit Document', icon: FileText },
    { id: 'claims', labelAr: 'الأدلة والتناقضات', labelEn: 'Evidence & Claims', icon: AlertTriangle },
    { id: 'langgraph', labelAr: 'مسار الوكيل (DAG)', labelEn: 'LangGraph DAG', icon: Cpu },
    { id: 'hitl', labelAr: 'بوابة الاعتماد (HITL)', labelEn: 'HITL Gate', icon: CheckCircle2, badge: pendingHITLCount },
    { id: 'security', labelAr: 'مختبر الأمان', labelEn: 'Security Lab', icon: Shield },
    { id: 'specs', labelAr: 'المعمارية وعقود MCP', labelEn: 'Specs & MCP', icon: Terminal },
  ];

  return (
    <header className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Strictly compliant with Top Bar Contract: 3 zones separated by gap-8 */}
        <div className="flex items-center justify-between gap-8 h-16">
          
          {/* Zone 1: Single text element wordmark */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-indigo-600 flex items-center justify-center text-white shadow-sm shadow-cyan-500/20">
              <Shield className="w-4 h-4" />
            </div>
            <button 
              onClick={() => onTabChange('dashboard')} 
              className="text-start font-bold tracking-tight text-white hover:text-cyan-300 transition-colors whitespace-nowrap shrink-0"
            >
              <span className="text-lg">{isAr ? 'مِجهر' : 'MIJHAR'}</span>
              <span className="text-xs text-slate-400 font-normal mx-2 hidden sm:inline">
                {isAr ? '· وكيل تدقيق الأدلة المستقل' : '· Autonomous Evidence Audit Agent'}
              </span>
            </button>
          </div>

          {/* Zone 2: Navigation Links, single line */}
          <nav className="hidden lg:flex items-center gap-1 xl:gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onTabChange(item.id)}
                  className={`relative flex items-center gap-2 px-3 py-1.5 text-xs xl:text-sm font-medium rounded-md transition-colors whitespace-nowrap shrink-0 ${
                    isActive
                      ? 'bg-slate-800 text-cyan-400 shadow-sm shadow-black/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{isAr ? item.labelAr : item.labelEn}</span>
                  {item.badge && item.badge > 0 ? (
                    <span className="px-1.5 py-0.2 text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 rounded border border-amber-500/30">
                      {item.badge}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </nav>

          {/* Zone 3: Primary Action / Controls */}
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={onToggleLanguage}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono font-medium text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-700/60 rounded-lg transition-colors whitespace-nowrap shrink-0"
              title={isAr ? 'التبديل إلى الإنجليزية' : 'Switch to Arabic'}
            >
              <Globe className="w-3.5 h-3.5 text-cyan-400" />
              <span>{isAr ? 'English' : 'عربي'}</span>
            </button>

            <button
              onClick={() => onTabChange('upload')}
              className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-lg shadow-sm shadow-cyan-500/20 transition-colors whitespace-nowrap shrink-0"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isAr ? 'تدقيق وثيقة جديدة' : 'New Audit Job'}</span>
            </button>
          </div>

        </div>

        {/* Mobile Navigation Strip */}
        <div className="lg:hidden flex items-center gap-1 py-2 overflow-x-auto border-t border-slate-900">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md whitespace-nowrap shrink-0 ${
                  isActive
                    ? 'bg-slate-800 text-cyan-400'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{isAr ? item.labelAr : item.labelEn}</span>
                {item.badge && item.badge > 0 ? (
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                ) : null}
              </button>
            );
          })}
        </div>

      </div>
    </header>
  );
};
