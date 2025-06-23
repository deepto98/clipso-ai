
import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Video, Sparkles } from 'lucide-react';

const Navbar = () => {
  return (
    <nav className="w-full py-4 px-6 flex items-center justify-between bg-background/40 backdrop-blur-xl border-b border-border/40 sticky top-0 z-50 shadow-sm">
      <div className="flex items-center gap-2 pl-2">
        <Link to="/" className="flex items-center gap-2 font-bold text-xl text-gradient group">
          <Video className="h-6 w-6 text-purple-400 group-hover:text-purple-300 transition-colors" />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-purple-600">Clipso</span>
        </Link>
      </div>
      
      <div className="hidden md:flex items-center gap-8 text-sm font-medium">
        <Link to="/" className="text-foreground hover:text-purple-400 transition-colors relative after:absolute after:bottom-0 after:left-0 after:h-[2px] after:w-0 hover:after:w-full after:bg-purple-400 after:transition-all">
          Home
        </Link>
        <Link to="/create" className="text-foreground hover:text-purple-400 transition-colors relative after:absolute after:bottom-0 after:left-0 after:h-[2px] after:w-0 hover:after:w-full after:bg-purple-400 after:transition-all">
          Create
        </Link>
        <a href="#features" className="text-foreground hover:text-purple-400 transition-colors relative after:absolute after:bottom-0 after:left-0 after:h-[2px] after:w-0 hover:after:w-full after:bg-purple-400 after:transition-all">
          Features
        </a>
      </div>
      
      <div className="flex items-center gap-4">
        <Link to="/create">
          <Button size="sm" className="gap-2 bg-purple-600 hover:bg-purple-700 button-glow transition-all">
            <Sparkles className="h-4 w-4" />
            New Video
          </Button>
        </Link>
      </div>
    </nav>
  );
};

export default Navbar;
