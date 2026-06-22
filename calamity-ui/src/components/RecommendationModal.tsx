import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, MapPin, Activity } from "lucide-react";

interface RecommendationModalProps {
  results: any;
  formData: any;
  onSuggestionClick: (updates: any) => void;
  onClose: () => void;
}

export default function RecommendationModal({ results, formData, onSuggestionClick, onClose }: RecommendationModalProps) {
  if (!results || !results.suggested_alternatives) return null;

  const { same_country_disasters, same_disaster_countries } = results.suggested_alternatives;
  
  const shouldShow = results.historical_context.length === 0 && 
    (same_country_disasters?.length > 0 || same_disaster_countries?.length > 0);

  if (!shouldShow) return null;

  return (
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/70 backdrop-blur-sm"
      >
        <motion.div 
          initial={{ scale: 0.95, opacity: 0, y: 10 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 10 }}
          className="bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl p-6 md:p-8 max-w-lg w-full relative overflow-hidden"
        >
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500 to-orange-500" />
          
          <div className="flex flex-col items-center text-center space-y-4 mb-8 mt-2">
            <div className="w-12 h-12 bg-red-500/10 rounded-full flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-red-500" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-zinc-100 mb-2">No Exact Match Found</h2>
              <p className="text-sm text-zinc-400 leading-relaxed max-w-md mx-auto">
                The RAG Engine could not locate historical records for <strong className="text-zinc-200">{formData.disaster_type}</strong> in <strong className="text-zinc-200">{formData.country}</strong>. 
                The Math Engine has calculated theoretical impact, but we recommend analyzing an existing historical profile.
              </p>
            </div>
          </div>

          <div className="space-y-6">
            {same_country_disasters && same_country_disasters.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <MapPin className="w-3.5 h-3.5" />
                  Try other disasters in {formData.country}
                </h3>
                <div className="flex flex-wrap gap-2">
                  {same_country_disasters.map((disaster: string) => (
                    <button
                      key={disaster}
                      onClick={() => {
                        onSuggestionClick({ disaster_type: disaster });
                        onClose();
                      }}
                      className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-md transition-colors border border-zinc-700 hover:border-zinc-500"
                    >
                      {disaster}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {same_disaster_countries && same_disaster_countries.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5" />
                  Try {formData.disaster_type} in other regions
                </h3>
                <div className="flex flex-wrap gap-2">
                  {same_disaster_countries.map((country: string) => (
                    <button
                      key={country}
                      onClick={() => {
                        onSuggestionClick({ country: country });
                        onClose();
                      }}
                      className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-md transition-colors border border-zinc-700 hover:border-zinc-500"
                    >
                      {country}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          <div className="mt-8 pt-6 border-t border-zinc-800 flex justify-center">
            <button 
              onClick={onClose}
              className="text-xs text-zinc-500 hover:text-zinc-300 font-medium transition-colors"
            >
              Continue with theoretical calculation only
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
