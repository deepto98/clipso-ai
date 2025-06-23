import React from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import AppContainer from "@/components/layout/AppContainer";
import { Card, CardContent } from "@/components/ui/card";

// We'll use regular JSX rather than the tabler icons to avoid compatibility issues
const Index = () => {
  return (
    <AppContainer fullWidth>
      {/* Background effects */}
      <div className="absolute top-[5%] left-[10%] w-[40vw] h-[40vw] rounded-full filter blur-3xl opacity-10 bg-[rgb(125,80,230)]" />
      <div className="absolute bottom-[10%] right-[5%] w-[35vw] h-[35vw] rounded-full filter blur-3xl opacity-10 bg-[rgb(80,160,255)]" />

      {/* Hero Section */}
      <div className="relative flex flex-col items-center justify-center min-h-[90vh] px-4 py-20 overflow-hidden">
        <div className="absolute top-0 right-0 w-full h-full pointer-events-none">
          <svg
            width="100%"
            height="100%"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
          >
            <path
              d="M0,0 L100,0 L100,100 L0,100 Z"
              fill="none"
              stroke="rgba(125, 80, 230, 0.1)"
              strokeWidth="0.2"
            />
          </svg>
        </div>

        <div className="text-center max-w-4xl mx-auto mb-8">
          <div className="inline-flex items-center px-3 py-1 mb-6 text-sm rounded-full bg-purple-900/20 text-purple-300 border border-purple-800/30">
            <span className="mr-2">✨</span>
            <span>Reels Optimized Video Editor</span>
            <span className="flex h-2 w-2 ml-2">
              <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-purple-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
            </span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
            Transform Videos with{" "}
            <span className="text-gradient shimmer">AI Magic</span>
          </h1>

          <p className="text-xl md:text-2xl mb-10 text-gray-300/80 max-w-3xl mx-auto">
            Instantly generate captions, add B-roll images, and create stunning{" "}
            <span className="text-gradient">Instagram-ready content</span> in
            seconds.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 mb-16">
          <Link to="/create">
            <Button
              size="lg"
              className="h-14 px-8 gap-2 bg-purple-600 hover:bg-purple-700 button-glow"
            >
              Start Creating →
            </Button>
          </Link>

          <Link to="#showcase">
            <Button
              variant="outline"
              size="lg"
              className="h-14 px-8 gap-2 backdrop-blur-md border-purple-500/20 hover:bg-purple-500/10"
            >
              ▶️ See Examples
            </Button>
          </Link>
        </div>

        {/* AI Video Showcase */}
        <div
          id="showcase"
          className="w-full max-w-6xl mx-auto glass-card p-8 cosmic-gradient"
        >
          <div className="flex flex-col md:flex-row gap-8 items-center">
            <div className="w-full md:w-7/12">
              <div className="card-3d transition-all hover:-translate-y-2 hover:shadow-lg">
                <Card className="aspect-[9/16] bg-gradient-to-br from-purple-800/30 to-blue-900/40 rounded-xl flex flex-col items-center justify-center p-6 relative group">
                  <div className="w-20 h-20 bg-purple-600/20 backdrop-blur-lg rounded-full flex items-center justify-center mb-6">
                    <span className="text-white text-4xl">✨</span>
                  </div>

                  <h3 className="text-2xl font-bold text-white mb-3 text-center">
                    Create Engaging Content
                  </h3>

                  <p className="text-white/80 text-center mb-6">
                    Turn your talking videos into captivating social media
                    content with auto-captions and AI-generated visuals
                  </p>

                  <div className="flex flex-wrap gap-2 justify-center">
                    {["Captions", "B-Roll", "Export"].map((tag, i) => (
                      <span
                        key={i}
                        className="px-3 py-1 text-xs rounded-full bg-white/10 text-white/80 border border-white/20"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  {/* Instagram Reels Icon */}
                  <div className="absolute top-4 right-4 text-white/80">
                    <span className="text-xl">📱</span>
                  </div>
                </Card>
              </div>
              <div className="mt-4 text-center">
                <span className="inline-flex items-center px-3 py-1 text-xs rounded-full bg-purple-900/20 text-purple-300 border border-purple-800/30">
                  <span className="mr-1">📱</span>
                  Perfect for Instagram Reels
                </span>
              </div>
            </div>

            <div className="w-full md:w-5/12 space-y-6">
              <h2 className="text-3xl font-bold">
                <span className="text-gradient">AI-Powered</span> Video
                Enhancement
              </h2>

              <p className="text-gray-300/80">
                Clipso uses advanced AI to transform your talking videos into
                engaging content with perfectly synchronized captions and
                contextually relevant B-roll imagery.
              </p>

              <ul className="space-y-4">
                {[
                  { icon: "📹", text: "Record directly from your device" },
                  { icon: "🧠", text: "AI transcription with perfect timing" },
                  { icon: "✨", text: "Auto-generated B-roll visuals" },
                  { icon: "⬇️", text: "Export ready for social media" },
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <div className="p-2 bg-purple-900/20 text-purple-300 rounded-lg">
                      <span>{item.icon}</span>
                    </div>
                    <span>{item.text}</span>
                  </li>
                ))}
              </ul>

              <div className="pt-4">
                <Link to="/create">
                  <Button className="w-full gap-2 bg-purple-600 hover:bg-purple-700 button-glow">
                    Create a New Video →
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-20 px-4">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-4xl font-bold mb-6">How Clipso Works</h2>
          <p className="text-xl text-gray-300/80">
            Our AI-powered workflow transforms your raw footage into social
            media-ready content in just three simple steps.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {[
            {
              icon: "📹",
              title: "Record or Upload",
              description:
                "Start with your raw video from any device. Record directly in your browser or upload existing footage.",
            },
            {
              icon: "🧠",
              title: "AI Processing",
              description:
                "Our AI automatically transcribes your speech, generates captions, and creates matching B-roll imagery.",
            },
            {
              icon: "⬇️",
              title: "Export & Share",
              description:
                "Download your enhanced video ready for Instagram Reels, TikTok, YouTube Shorts and more.",
            },
          ].map((feature, i) => (
            <div key={i}>
              <div className="hover-scale card-gradient h-full transition-all hover:-translate-y-2 hover:shadow-xl">
                <Card className="h-full border-0 bg-transparent">
                  <CardContent className="pt-8 pb-8 text-center h-full flex flex-col">
                    <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white h-16 w-16 rounded-2xl flex items-center justify-center mb-6 mx-auto shadow-lg shadow-purple-700/20">
                      <span className="text-2xl">{feature.icon}</span>
                    </div>

                    <h3 className="text-2xl font-bold mb-4">{feature.title}</h3>

                    <p className="text-gray-300/80 mb-6 flex-grow">
                      {feature.description}
                    </p>

                    <div className="w-1/3 h-1 bg-gradient-to-r from-purple-600 to-blue-600 mx-auto rounded-full"></div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center mt-16">
          <Link to="/create">
            <Button
              size="lg"
              className="h-14 px-8 gap-2 bg-purple-600 hover:bg-purple-700 button-glow"
            >
              Create a New Video →
            </Button>
          </Link>
        </div>
      </div>
    </AppContainer>
  );
};

export default Index;
