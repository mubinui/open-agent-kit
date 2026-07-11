import { useState } from 'react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { WorkflowCanvas } from './components/WorkflowCanvas';
import { PropertiesPanel } from './components/PropertiesPanel';
import { ChatPanel } from './components/ChatPanel';
import { LibraryModal } from './components/LibraryModal';
import { LaunchpadPanel } from './components/LaunchpadPanel';
import { ExecutionTimeline } from './components/ExecutionTimeline';

import { LandingPage } from './components/LandingPage';
import { AuthModal } from './components/AuthModal';
import { LiveLlmTester } from './components/LiveLlmTester';
import { DeploymentManager } from './components/DeploymentManager';

import { ReactFlowProvider } from '@xyflow/react';
import '@xyflow/react/dist/style.css'; // Ensure styles are available

// Create context for library modal
import { createContext, useContext } from 'react';

interface LibraryModalContextType {
  openLibraryModal: (tab?: 'tools' | 'agents' | 'functions' | 'prompts' | 'providers' | 'ops') => void;
}

export const LibraryModalContext = createContext<LibraryModalContextType>({
  openLibraryModal: () => { },
});

export const useLibraryModal = () => useContext(LibraryModalContext);

function App() {
  const [libraryModalOpen, setLibraryModalOpen] = useState(false);
  const [libraryModalTab, setLibraryModalTab] = useState<'tools' | 'agents' | 'functions' | 'prompts' | 'providers' | 'ops'>('tools');

  // Navigation views state: 'landing' | 'canvas' | 'tester' | 'deploy'
  const [currentScreen, setCurrentScreen] = useState<'landing' | 'canvas' | 'tester' | 'deploy'>('landing');
  const [authModalOpen, setAuthModalOpen] = useState(false);

  const openLibraryModal = (tab: 'tools' | 'agents' | 'functions' | 'prompts' | 'providers' | 'ops' = 'tools') => {
    setLibraryModalTab(tab);
    setLibraryModalOpen(true);
  };

  return (
    <LibraryModalContext.Provider value={{ openLibraryModal }}>
      <ReactFlowProvider>
        <div className="flex h-screen w-screen bg-[var(--color-canvas-bg)] overflow-hidden flex-col relative">
          {/* Main Global Topbar Header */}
          <Header
            onOpenLanding={() => setCurrentScreen('landing')}
            onOpenTester={() => setCurrentScreen('tester')}
            onOpenDeploy={() => setCurrentScreen('deploy')}
          />

          {/* Active Workspaces Wrapper */}
          <div className="flex flex-grow h-full overflow-hidden relative">
            {/* Standard Canvas/Studio layout */}
            <Sidebar />
            <main className="flex-grow h-full relative flex min-w-0">
              <LaunchpadPanel />
              <div className="flex-1 relative min-w-0">
                <WorkflowCanvas />
                <PropertiesPanel />
                <ChatPanel />
                <ExecutionTimeline />
              </div>
            </main>

            {/* View Overlay 1: Welcome Premium Landing Page */}
            {currentScreen === 'landing' && (
              <LandingPage
                onEnterStudio={() => setCurrentScreen('canvas')}
                onOpenTester={() => setCurrentScreen('tester')}
                onOpenDeploy={() => setCurrentScreen('deploy')}
                onOpenAuth={() => setAuthModalOpen(true)}
              />
            )}

            {/* View Overlay 2: Live LLM Real-time Validation Sandbox */}
            {currentScreen === 'tester' && (
              <LiveLlmTester onClose={() => setCurrentScreen('canvas')} />
            )}

            {/* View Overlay 3: Deployment Manager / Export Hub */}
            {currentScreen === 'deploy' && (
              <DeploymentManager onClose={() => setCurrentScreen('canvas')} />
            )}
          </div>
        </div>

        {/* Global Access Modals */}
        <LibraryModal
          isOpen={libraryModalOpen}
          onClose={() => setLibraryModalOpen(false)}
          initialTab={libraryModalTab}
        />

        <AuthModal
          isOpen={authModalOpen}
          onClose={() => setAuthModalOpen(false)}
        />
      </ReactFlowProvider>
    </LibraryModalContext.Provider>
  );
}

export default App;
