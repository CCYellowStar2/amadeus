import React, { useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import ConfigEditor from './components/ConfigEditor';
import Navbar from './components/Navbar';
import { useStore } from './store';
import { useTranslation } from 'react-i18next';
import EmptyState from './components/EmptyState';
import Terminal from './components/Terminal';
import TerminalToggleButton from './components/TerminalToggleButton';

const App: React.FC = () => {
  const { t } = useTranslation();
  const { selectedClass, initialize, loading } = useStore();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isTerminalVisible, setTerminalVisible] = useState(false);

  useEffect(() => {
    const init = async () => {
      // If not in Electron, initialize right away.
      if (!window.api) {
        console.log("Running in browser, initializing directly.");
        initialize();
        return;
      }
      
      // If in Electron, wait for the 'api-ready' event from the preload script
      window.addEventListener('api-ready', initialize, { once: true });
    };
    init();

    return () => {
      // Cleanup listener if component unmounts before event fires
      window.removeEventListener('api-ready', initialize);
    }
  }, [initialize]);

  if (loading.classes) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">{t('common.loading')}</h2>
          <p className="text-muted-foreground">{t('common.loadingDesc')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
      
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar onMenuClick={() => setSidebarOpen(!sidebarOpen)} />
        
        <main className="flex-1 overflow-auto p-4 md:p-6">
          {selectedClass ? (
            <ConfigEditor />
          ) : (
            <EmptyState
              title={t('common.welcome')}
              description={t('common.selectConfig')}
              icon="Settings"
            />
          )}
        </main>
      </div>
      <Terminal isVisible={isTerminalVisible} />
      <TerminalToggleButton onClick={() => setTerminalVisible(!isTerminalVisible)} />
    </div>
  );
};

export default App;