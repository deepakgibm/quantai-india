export interface PriceChangeDetails {
  price: number;
  previousClose: number;
  change: number;
  changePercent: number;
  direction: 'up' | 'down' | 'flat';
}

/**
 * Centralized utility to calculate stock price changes, directions, and color states.
 * Reconciles API provided values with computed values and performs consistency checks.
 */
export function calculatePriceChange(
  currentPrice: number | null | undefined,
  previousClose: number | null | undefined,
  apiChangePercent?: number | null | undefined
): PriceChangeDetails {
  const price = typeof currentPrice === 'number' && !isNaN(currentPrice) ? currentPrice : 0;
  let prevClose = typeof previousClose === 'number' && !isNaN(previousClose) ? previousClose : 0;

  // Round inputs to 2 decimal places to resolve float precision issues
  const roundedPrice = Math.round(price * 100) / 100;
  let roundedPrevClose = Math.round(prevClose * 100) / 100;

  let changePercent = 0;

  // 1. Reconstruct previousClose if missing but apiChangePercent is present
  if (typeof apiChangePercent === 'number' && !isNaN(apiChangePercent)) {
    const roundedApiPct = Math.round(apiChangePercent * 100) / 100;
    if (roundedPrevClose <= 0 && roundedPrice > 0 && roundedApiPct !== 0) {
      roundedPrevClose = Math.round((roundedPrice / (1 + roundedApiPct / 100)) * 100) / 100;
    }
    changePercent = roundedApiPct;
  } else if (roundedPrevClose > 0) {
    changePercent = Math.round(((roundedPrice - roundedPrevClose) / roundedPrevClose) * 100 * 100) / 100;
  }

  // 2. Reject inconsistent values if both are present and differ significantly
  if (roundedPrevClose > 0 && typeof apiChangePercent === 'number' && !isNaN(apiChangePercent)) {
    const calculatedPct = ((roundedPrice - roundedPrevClose) / roundedPrevClose) * 100;
    // Reject and override if discrepancy is greater than 0.5%
    if (Math.abs(calculatedPct - apiChangePercent) > 0.5) {
      console.warn(
        `[MarketPriceUtil] Rejecting inconsistent apiChangePercent for price=${roundedPrice}, prevClose=${roundedPrevClose}: ` +
        `API returned ${apiChangePercent}% but calculated was ${calculatedPct.toFixed(2)}%. Recalculating.`
      );
      changePercent = Math.round(calculatedPct * 100) / 100;
    }
  }

  const change = Math.round((roundedPrice - roundedPrevClose) * 100) / 100;

  let direction: 'up' | 'down' | 'flat' = 'flat';
  if (change > 0.0001) {
    direction = 'up';
  } else if (change < -0.0001) {
    direction = 'down';
  }

  // Developer logging (Requirement: Add Logging)
  console.debug(`[MarketPriceUtil] Symbol details:`, {
    price: roundedPrice,
    previousClose: roundedPrevClose,
    apiChangePercent,
    calculatedChangePercent: changePercent,
    change,
    direction,
    timestamp: new Date().toISOString()
  });

  return {
    price: roundedPrice,
    previousClose: roundedPrevClose,
    change,
    changePercent,
    direction
  };
}
