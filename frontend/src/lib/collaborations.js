// Shared view logic for collaborations (the `campaigns` records in the API).
// The brand is always the payer and the reviewer. The creator delivers.
import { formatINR } from './format';

export const ACTIVE_STATES = ['requested', 'accepted', 'payment_pending', 'paid', 'in_progress', 'link_submitted', 'link_verified'];
export const IN_FLIGHT_STATES = ['paid', 'in_progress', 'link_submitted', 'link_verified'];

export const STATUS_META = {
  requested: { label: 'Requested', tone: 'amber', step: 0 },
  accepted: { label: 'Awaiting payment', tone: 'orange', step: 1 },
  payment_pending: { label: 'Awaiting payment', tone: 'orange', step: 1 },
  paid: { label: 'In production', tone: 'plum', step: 2 },
  in_progress: { label: 'In production', tone: 'plum', step: 2 },
  link_submitted: { label: 'Content to review', tone: 'orange', step: 3 },
  link_verified: { label: 'Approved', tone: 'sage', step: 4 },
  completed: { label: 'Completed', tone: 'sage', step: 5 },
  disputed: { label: 'In dispute', tone: 'brick', step: -1 },
  cancelled: { label: 'Cancelled', tone: 'neutral', step: -1 },
};

export const LIFECYCLE = ['Request', 'Payment', 'Production', 'Review', 'Approved', 'Done'];

export const TYPE_LABEL = { paid: 'Paid', barter_product: 'Barter · product', barter_service: 'Barter · service' };

export const isBarter = (c) => c.campaignType !== 'paid';

export const counterpartName = (c, viewerUserRole) => {
  // The viewer is either the sender or the receiver; show the other side.
  const viewerIsSender = c.senderType === viewerUserRole;
  return viewerIsSender ? c.receiverName : c.senderName;
};

export const counterpartInstagram = (c, viewerUserRole) =>
  (c.senderType === viewerUserRole ? c.receiverInstagram : c.senderInstagram) || null;

export const amountFor = (c) => (c.campaignType === 'paid' ? c.escrowAmount || c.budget : c.barterFee);

/**
 * What happens next on a collaboration, from the viewer's side.
 * Returns { who: 'you' | 'them' | 'orange' | 'none', label, action? }.
 */
export const nextStep = (c, role, { incoming } = {}) => {
  const business = role === 'business';
  switch (c.status) {
    case 'requested':
      return incoming
        ? { who: 'you', label: 'Accept or decline this request', action: 'respond' }
        : { who: 'them', label: `Waiting for the ${business ? 'creator' : 'brand'} to respond` };
    case 'accepted':
    case 'payment_pending':
      return business
        ? { who: 'you', label: `Pay ${formatINR(amountFor(c))} to start`, action: 'pay' }
        : { who: 'them', label: 'Waiting for the brand to pay' };
    case 'paid':
    case 'in_progress':
      if (c.campaignType === 'barter_product' && !c.shippingDetails) {
        return business
          ? { who: 'you', label: 'Add shipping details for the product', action: 'ship' }
          : { who: 'them', label: 'Waiting for the brand to ship the product' };
      }
      if (c.campaignType === 'barter_product' && !c.productReceived && !business) {
        return { who: 'you', label: 'Confirm you received the product', action: 'receive' };
      }
      return business
        ? { who: 'them', label: 'The creator is making the content' }
        : { who: 'you', label: 'Submit your content link', action: 'submit' };
    case 'link_submitted':
      return business
        ? { who: 'you', label: 'Review the submitted content', action: 'verify' }
        : { who: 'them', label: 'The brand is reviewing your content' };
    case 'link_verified':
      return business
        ? { who: 'you', label: c.campaignType === 'paid' ? 'Complete and release the payout' : 'Mark the collaboration complete', action: 'complete' }
        : { who: 'them', label: 'Waiting for the brand to complete' };
    case 'completed':
      return { who: 'none', label: 'Completed', action: 'rate' };
    case 'disputed':
      return { who: 'orange', label: 'Orange is reviewing this dispute' };
    default:
      return { who: 'none', label: 'Cancelled' };
  }
};
