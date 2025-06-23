
import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import AppContainer from "@/components/layout/AppContainer";

const NotFound = () => {
  return (
    <AppContainer>
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <h1 className="text-6xl font-bold text-purple-600">404</h1>
        <h2 className="text-2xl font-semibold mt-4 mb-6">Page Not Found</h2>
        <p className="text-muted-foreground max-w-lg mb-8">
          The page you are looking for doesn't exist or has been moved.
          Let's get you back on track.
        </p>
        <Link to="/">
          <Button className="px-8 bg-purple-600 hover:bg-purple-700">
            Return to Home
          </Button>
        </Link>
      </div>
    </AppContainer>
  );
};

export default NotFound;
