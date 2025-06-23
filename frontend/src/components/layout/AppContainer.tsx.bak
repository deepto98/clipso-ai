
import React from 'react';
import Navbar from './Navbar';

interface AppContainerProps {
  children: React.ReactNode;
  fullWidth?: boolean;
}

const AppContainer = ({ children, fullWidth = false }: AppContainerProps) => {
  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground relative overflow-hidden">
      {/* Futuristic background elements */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-purple-900/20 rounded-full filter blur-3xl"></div>
        <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-clipso-800/20 rounded-full filter blur-3xl"></div>
        <div className="absolute top-1/2 left-1/4 w-64 h-64 bg-purple-700/10 rounded-full filter blur-3xl"></div>
      </div>
      
      <Navbar />
      <div className={`flex-1 z-10 ${fullWidth ? 'w-full px-4' : 'container px-4 py-6 md:py-8'}`}>
        {children}
      </div>
      <footer className="w-full py-6 px-6 border-t border-white/10 text-center text-sm text-muted-foreground z-10 backdrop-blur-md bg-background/40">
        <div className="container mx-auto max-w-5xl">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6 text-left">
            <div>
              <h3 className="font-semibold text-purple-400 mb-2">About Clipso</h3>
              <p className="text-sm opacity-80">
                Clipso transforms your talking videos with AI-powered captions and B-roll imagery,
                making your content more engaging and professional in just minutes.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-purple-400 mb-2">Features</h3>
              <ul className="opacity-80 space-y-1">
                <li>• Auto-generated captions</li>
                <li>• Contextual B-roll images</li>
                <li>• Multiple aspect ratios</li>
                <li>• One-click social sharing</li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold text-purple-400 mb-2">Quick Links</h3>
              <ul className="opacity-80 space-y-1">
                <li>• <a href="/" className="hover:text-purple-400 transition-colors">Home</a></li>
                <li>• <a href="/create" className="hover:text-purple-400 transition-colors">Create Video</a></li>
                <li>• <a href="#features" className="hover:text-purple-400 transition-colors">Features</a></li>
              </ul>
            </div>
          </div>
          <div className="pt-4 border-t border-white/5 flex flex-col md:flex-row justify-between items-center">
            <div>
              © {new Date().getFullYear()} Clipso - AI Video Captions & B-Roll Generator
            </div>
            <div className="mt-2 md:mt-0 flex items-center gap-1">
              Created by <a href="https://github.com/deepto98" target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 font-medium transition-colors">
                Deepto <span aria-label="GitHub">
                  <svg className="inline-block w-4 h-4 ml-1" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                  </svg>
                </span>
              </a>
              <span className="mx-1">|</span>
              <a href="https://twitter.com/deepto98" target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 font-medium transition-colors">
                <span aria-label="Twitter">
                  <svg className="inline-block w-4 h-4" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                    <path d="M23.643 4.937c-.835.37-1.732.62-2.675.733.962-.576 1.7-1.49 2.048-2.578-.9.534-1.897.922-2.958 1.13-.85-.904-2.06-1.47-3.4-1.47-2.572 0-4.658 2.086-4.658 4.66 0 .364.042.718.12 1.06-3.873-.195-7.304-2.05-9.602-4.868-.4.69-.63 1.49-.63 2.342 0 1.616.823 3.043 2.072 3.878-.764-.025-1.482-.234-2.11-.583v.06c0 2.257 1.605 4.14 3.737 4.568-.392.106-.803.162-1.227.162-.3 0-.593-.028-.877-.082.593 1.85 2.313 3.198 4.352 3.234-1.595 1.25-3.604 1.995-5.786 1.995-.376 0-.747-.022-1.112-.065 2.062 1.323 4.51 2.093 7.14 2.093 8.57 0 13.255-7.098 13.255-13.254 0-.2-.005-.402-.014-.602.91-.658 1.7-1.477 2.323-2.41z"/>
                  </svg>
                </span>
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default AppContainer;
